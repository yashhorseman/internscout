"""Ingest every board in sources.yaml.

    python -m app.ingest.run
"""
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.db import connect
from app.ingest import greenhouse, lever, remoteok
from app.ingest.fetch import get_json, make_client
from app.ingest.store import close_missing, upsert

log = logging.getLogger("ingest")
SOURCES_FILE = Path(__file__).with_name("sources.yaml")
ADAPTERS = {"greenhouse": greenhouse, "lever": lever, "remoteok": remoteok}


def load_boards(path: Path = SOURCES_FILE) -> list[dict]:
    return yaml.safe_load(path.read_text())


def ingest_board(conn, client, board: dict) -> dict:
    """One board, start to finish. Never raises: failures are recorded."""
    source = board["source"]
    adapter = ADAPTERS[source]
    started = datetime.now(timezone.utc)
    stats = {"fetched": 0, "new": 0, "changed": 0, "closed": 0, "error": None}
    try:
        raw_items = adapter.items(get_json(client, adapter.url(board)))
        postings, bad = {}, []
        for item in raw_items:
            try:
                job = adapter.to_posting(item, board)
                postings[job.source_job_id] = job  # also removes duplicates
            except Exception as exc:
                bad.append(f"{item.get('id')}: {type(exc).__name__}")
        # all of this board's writes succeed together or not at all
        with conn.transaction():
            for job in postings.values():
                outcome = upsert(conn, job, started)
                if outcome != "unchanged":
                    stats[outcome] += 1
            stats["fetched"] = len(postings)
            if bad:
                # a posting we could not read must not be mistaken for a removed one
                stats["error"] = f"{len(bad)} unreadable items, closed nothing: {bad[:3]}"
            else:
                stats["closed"] = close_missing(conn, source, board["board"], started,
                                                len(postings), board.get("expire_after_days"))
    except Exception as exc:
        stats = {"fetched": 0, "new": 0, "changed": 0, "closed": 0,
                 "error": f"{type(exc).__name__}: {exc}"[:500]}
    conn.execute(
        "insert into ingest_runs (source, board, started_at, finished_at, fetched,"
        " new_jobs, changed_jobs, closed_jobs, error)"
        " values (%s, %s, %s, now(), %s, %s, %s, %s, %s)",
        (source, board["board"], started, stats["fetched"], stats["new"],
         stats["changed"], stats["closed"], stats["error"]),
    )
    return stats


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    failed = 0
    with connect() as conn, make_client() as client:
        for position, board in enumerate(load_boards()):
            if position:
                time.sleep(1)  # be gentle with the job boards
            s = ingest_board(conn, client, board)
            failed += bool(s["error"])
            log.info("%-10s %-32s fetched=%-4d new=%-4d changed=%-4d closed=%-4d %s",
                     board["source"], board["board"], s["fetched"], s["new"],
                     s["changed"], s["closed"], s["error"] or "")
        # Refresh planner statistics and merge the GIN index's pending entries.
        # Without this the planner stops using the full-text index after bulk writes.
        conn.execute("vacuum analyze jobs")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
