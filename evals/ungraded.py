"""Collect the (query, posting) pairs that later experiments surfaced and nobody has graded,
and write them out for a grader without saying where each came from.

    python -m evals.ungraded OUTPUT.jsonl
"""
import json
import random
import sys

from app.db import connect
from evals.common import AGENT_DIR, RESULTS, db_url, load_grades, load_queries, read_jsonl


def pairs() -> list[tuple[str, int]]:
    queries, grades = {q["id"] for q in load_queries()}, load_grades(extra=True)
    found = set()
    for name in ("rerank_passage_ungraded.json", "e6_ungraded.json"):
        if (RESULTS / name).exists():
            found |= {(q, j) for q, j in json.loads((RESULTS / name).read_text())}
    for run in [r for path in AGENT_DIR.parent.glob("*/runs.jsonl") for r in read_jsonl(path)]:
        if run["id"] in queries:
            found |= {(run["id"], j) for j in [c["job_id"] for c in run["cards"]] + run["found"][:10]}
    return sorted((q, j) for q, j in found if j not in grades.get(q, {}))


def main() -> None:
    queries = {q["id"]: q for q in load_queries()}
    wanted = pairs()
    random.Random(1).shuffle(wanted)
    wanted.sort(key=lambda pair: pair[0])  # grouped by query, shuffled within each
    with connect(db_url()) as conn, open(sys.argv[1], "w") as out:
        for query_id, job_id in wanted:
            title, company, location, remote, level, text = conn.execute(
                "select j.title, c.name, j.location_raw, j.is_remote, j.level, j.description_text from jobs j"
                " join companies c on c.id = j.company_id where j.id = %s", (job_id,)).fetchone()
            query = queries[query_id]
            out.write(json.dumps({"query_id": query_id, "search": query["text"], "filters": query.get("filters"),
                                  "job_id": job_id, "title": title, "company": company, "location": location,
                                  "remote": remote, "level": level, "description": text}) + "\n")
    print(f"{len(wanted)} pairs written")


if __name__ == "__main__":
    main()
