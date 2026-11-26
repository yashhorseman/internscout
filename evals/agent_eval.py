"""Send every benchmark query to the agent as a plain user message and keep what happened.

    python -m evals.agent_eval            # resumes: finished queries are skipped
    python -m evals.agent_report

Runs against the frozen evaluation database, so the grades apply.
"""
import json
import sys
import time

from app.agent import loop, store
from app.db import connect, migrate
from evals.common import AGENT_RUNS, NO_ANSWER, db_url, load_queries, read_jsonl

UNFINISHED = {"model_busy", "daily_limit", "budget"}
PAUSE = 5  # seconds between turns, to stay inside free limits


def run_one(conn, query: dict) -> dict:
    session = store.create_session(conn, is_test=True)
    trace: dict = {}
    started = time.perf_counter()
    reply = loop.run_turn(conn, session, query["text"], trace=trace)
    seconds = time.perf_counter() - started
    tools = [{"name": n, "args": a, "ok": ok} for n, a, ok in conn.execute(
        "select name, args, ok from tool_calls where session_id = %s order by id", (session,))]
    calls, tokens_in, tokens_out = conn.execute(
        "select count(*), coalesce(sum(input_tokens), 0), coalesce(sum(output_tokens), 0)"
        " from llm_calls where session_id = %s", (session,)).fetchone()
    return {"id": query["id"], "prompt": loop.PROMPT_VERSION, "seconds": round(seconds, 1),
            "outcome": reply["outcome"], "repairs": reply["repairs"],
            "claims_removed": reply["claims_removed"], "message": reply["message"],
            "clarifying_question": reply["clarifying_question"],
            "cards": [{k: c[k] for k in ("job_id", "title", "company", "why", "evidence")}
                      for c in reply["cards"]],
            "first_answer": trace["first_answer"], "rejections": trace["rejections"],
            "hit_step_limit": trace["hit_step_limit"],
            "found": trace["found"], "seen": trace["seen"], "tools": tools,
            "model_calls": calls, "input_tokens": tokens_in, "output_tokens": tokens_out}


def main() -> int:
    queries = load_queries() + read_jsonl(NO_ANSWER)
    done = {r["id"] for r in read_jsonl(AGENT_RUNS) if r["outcome"] not in UNFINISHED}
    todo = [q for q in queries if q["id"] not in done]
    with connect(db_url()) as conn:
        migrate(conn)
        AGENT_RUNS.parent.mkdir(parents=True, exist_ok=True)
        for number, query in enumerate(todo, start=1):
            record = run_one(conn, query)
            if record["outcome"] in ("model_busy",):  # overload passes; try once more
                time.sleep(60)
                record = run_one(conn, query)
            print(f"{number}/{len(todo)} {query['id']} {record['outcome']} {record['seconds']} s",
                  flush=True)
            if record["outcome"] in ("daily_limit", "budget"):
                print("stopping: run again when the limit resets")
                return 1
            kept = [r for r in read_jsonl(AGENT_RUNS) if r["id"] != query["id"]] + [record]
            AGENT_RUNS.write_text("".join(json.dumps(r) + "\n" for r in kept))
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
