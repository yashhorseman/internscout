"""The real app and database with a stand-in for the model, for load testing. No quota used.

    DATABASE_URL=... python scripts/fake_server.py --port 8010

The stand-in answers instantly: one search, then a reply quoting the first result. The results
therefore say nothing about speed with the real model.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

from app import api, llm  # noqa: E402
from app.agent import loop, tools  # noqa: E402
from app.ratelimit import SlidingWindow  # noqa: E402

VECTOR = tuple([1.0] + [0.0] * 767)


def generate(messages, *, system, tools=None, schema=None):
    if schema:
        jobs = next((m.result["jobs"] for m in reversed(messages) if m.role == "tool"), [])
        recs = [{"job_id": jobs[0]["job_id"], "why": "Matches.", "claims": [],
                 "evidence": " ".join(jobs[0]["snippet"].split()[:6])}] if jobs else []
        return llm.LLMResult(llm.Message("assistant", json.dumps(
            {"message": "Here is one.", "recommendations": recs})), model="fake")
    if messages[-1].role == "tool":
        return llm.LLMResult(llm.Message("assistant", "ready"), model="fake")
    call = llm.ToolCall("search_jobs", {"keywords": ["software", "engineer"],
                                        "query_text": messages[-1].text[:200]}, "1")
    return llm.LLMResult(llm.Message("assistant"), [call], "fake")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    real_turn = loop.run_turn
    loop.run_turn = lambda conn, sid, text: real_turn(conn, sid, text, generate=generate,
                                                      embed=lambda _t: VECTOR)
    api.limiter = SlidingWindow(10**9, 1)  # every simulated user comes from this machine
    api.log.disabled = True
    uvicorn.run(api.app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
