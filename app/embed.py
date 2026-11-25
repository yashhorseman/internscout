"""Embed every open posting whose embedding is missing or out of date.

    python -m app.embed [--priority-only] [--max N]

Safe to stop and restart: each batch is committed as soon as it is written.
India-based, intern and entry-level postings go first.
"""
import argparse
import logging
import sys
import time
from collections import deque

from app import llm
from app.db import connect

log = logging.getLogger("embed")

MAX_CHARS = 6000          # measured: no sampled posting exceeded 2,048 tokens
CHARS_PER_TOKEN = 4.4     # below the measured mean of 4.9, so we overestimate a little
REQUESTS_PER_MINUTE = 90  # free tier allows 100; keep a margin
TOKENS_PER_MINUTE = 27_000  # free tier allows 30,000
BATCH_TEXTS = 9           # two full batches fit in one minute
MAX_RETRIES = 5

PRIORITY = "(j.country_code = 'IN' or j.level in ('intern', 'entry'))"


def document_text(title, company, location, level, description) -> str:
    return (f"Title: {title}\nCompany: {company}\nLocation: {location or 'not stated'}\n"
            f"Level: {level}\n{description[:MAX_CHARS]}")


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 1


class MinuteLimiter:
    """Sleep as needed so the last 60 seconds stay under both limits."""

    def __init__(self, requests, tokens, clock=time.monotonic, sleep=time.sleep):
        self.requests, self.tokens = requests, tokens
        self.clock, self.sleep = clock, sleep
        self.window: deque = deque()  # (time, requests, tokens)

    def wait_for(self, requests: int, tokens: int) -> None:
        while True:
            now = self.clock()
            while self.window and now - self.window[0][0] >= 60:
                self.window.popleft()
            used_requests = sum(w[1] for w in self.window)
            used_tokens = sum(w[2] for w in self.window)
            fits = used_requests + requests <= self.requests and used_tokens + tokens <= self.tokens
            if fits or not self.window:
                self.window.append((now, requests, tokens))
                return
            self.sleep(60 - (now - self.window[0][0]) + 0.1)


def next_batch(conn, priority_only: bool, size: int) -> list[tuple]:
    where = f"and {PRIORITY}" if priority_only else ""
    return conn.execute(
        f"""
        select j.id, j.content_hash, j.title, c.name, j.location_raw, j.level, j.description_text
        from jobs j join companies c on c.id = j.company_id
        where j.status = 'open' and j.embedding_stale {where}
        order by coalesce({PRIORITY}, false) desc, j.id
        limit %s
        """,
        (size,),
    ).fetchall()


def _log_call(conn, started: float, ok: bool, error: str | None = None) -> None:
    conn.execute(
        "insert into llm_calls (kind, model, latency_ms, ok, error) values ('embed', %s, %s, %s, %s)",
        (llm.EMBED_MODEL, int((time.monotonic() - started) * 1000), ok, error and error[:500]),
    )


def run(conn, priority_only=False, max_jobs=None, embed_fn=llm.embed, limiter=None,
        sleep=time.sleep) -> dict:
    limiter = limiter or MinuteLimiter(REQUESTS_PER_MINUTE, TOKENS_PER_MINUTE)
    done, retries, stopped = 0, 0, None
    while max_jobs is None or done < max_jobs:
        size = BATCH_TEXTS if max_jobs is None else min(BATCH_TEXTS, max_jobs - done)
        rows = next_batch(conn, priority_only, size)
        if not rows:
            break
        texts = [document_text(*row[2:]) for row in rows]
        limiter.wait_for(len(texts), sum(map(estimate_tokens, texts)))
        started = time.monotonic()
        try:
            vectors = embed_fn(texts, llm.TASK_DOCUMENT)
        except llm.DailyQuotaExhausted as exc:
            _log_call(conn, started, False, str(exc))
            stopped = f"daily quota used up ({exc})"
            break
        except Exception as exc:  # rate limit or a passing network/server error
            _log_call(conn, started, False, f"{type(exc).__name__}: {exc}")
            retries += 1
            if retries > MAX_RETRIES:
                stopped = f"gave up after {MAX_RETRIES} retries: {type(exc).__name__}: {exc}"
                break
            wait = getattr(exc, "retry_after", None) or min(2 ** retries * 5, 120)
            log.warning("%s; retrying in %.0f s", type(exc).__name__, wait)
            sleep(wait)
            continue
        retries = 0
        _log_call(conn, started, True)
        with conn.transaction():
            for row, vector in zip(rows, vectors):
                # the hash check keeps the row stale if ingestion changed it meanwhile
                conn.execute(
                    "update jobs set embedding = %s::vector, embedding_model = %s,"
                    " embedding_stale = false where id = %s and content_hash = %s",
                    (str(vector), llm.EMBED_MODEL, row[0], row[1]),
                )
        done += len(rows)
        if done % 100 < len(rows):
            log.info("embedded %d", done)
    left = conn.execute(
        "select count(*) from jobs where status = 'open' and embedding_stale").fetchone()[0]
    return {"embedded": done, "still_stale": left, "stopped": stopped}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    for noisy in ("httpx", "httpx2", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority-only", action="store_true")
    parser.add_argument("--max", type=int)
    args = parser.parse_args()
    with connect() as conn:
        result = run(conn, args.priority_only, args.max)
        conn.execute("vacuum analyze jobs")
    log.info("done: %s", result)
    return 1 if result["stopped"] else 0


if __name__ == "__main__":
    sys.exit(main())
