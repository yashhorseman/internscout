"""p50 and p95 of search time per mode (query vectors already cached).

    python -m evals.latency
"""
import statistics
import time

from app.db import connect
from app.retrieval.search import MODES, search
from evals.common import db_url, load_queries, query_vectors

RUNS = 200


def main() -> None:
    queries = load_queries()
    vectors = query_vectors(queries)
    print("| Mode | p50 ms | p95 ms |\n|---|---|---|")
    with connect(db_url()) as conn:
        for mode in MODES:
            search(conn, "warm up", vectors[queries[0]["id"]], mode=mode)
            times = []
            for i in range(RUNS):
                query = queries[i % len(queries)]
                started = time.perf_counter()
                search(conn, query["text"], vectors[query["id"]], query.get("filters"), 10, mode,
                       keywords=query.get("keywords"))
                times.append((time.perf_counter() - started) * 1000)
            cuts = statistics.quantiles(times, n=100)
            print(f"| {mode} | {cuts[49]:.1f} | {cuts[94]:.1f} |", flush=True)


if __name__ == "__main__":
    main()
