"""Collect the candidates to label: the union of every mode's top 10 per query.

    python -m evals.pool
"""
import json
import random

from app.db import connect
from app.retrieval.search import MODES, search
from evals.common import POOL, db_url, load_queries, query_vectors


def main() -> None:
    queries = load_queries()
    vectors = query_vectors(queries)
    pool = {}
    with connect(db_url()) as conn:
        for query in queries:
            found = set()
            for mode in MODES:
                hits = search(conn, query["text"], vectors[query["id"]], query.get("filters"),
                              10, mode, keywords=query.get("keywords"))
                found |= {h.job_id for h in hits}
            ids = sorted(found)
            random.Random(query["id"]).shuffle(ids)  # order must not hint at any mode
            pool[query["id"]] = ids
    POOL.write_text(json.dumps(pool, indent=1))
    total = sum(map(len, pool.values()))
    print(f"{len(pool)} queries, {total} candidates to label (about {total * 10 / 3600:.1f} h at 10 s each)")


if __name__ == "__main__":
    main()
