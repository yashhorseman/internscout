"""Try a search from the terminal.

    python -m app.retrieval.cli "python backend internship" --mode hybrid --level intern
"""
import argparse
import logging
import sys

from app.db import connect
from app.retrieval.query import embed_query
from app.retrieval.search import MODES, search


def main() -> None:
    for noisy in ("httpx", "httpx2", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--mode", choices=MODES, default="hybrid")
    parser.add_argument("--level", choices=["intern", "entry", "mid", "senior", "unknown"])
    parser.add_argument("--country", help="two letters, for example IN")
    parser.add_argument("--company")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("-k", type=int, default=10)
    args = parser.parse_args()
    filters = {"level": args.level, "country_code": args.country and args.country.upper(),
               "company": args.company, "is_remote": True if args.remote else None}
    mode, vector = args.mode, None
    if mode != "keyword":
        try:
            vector = list(embed_query(args.query))
        except Exception as exc:  # degrade instead of failing
            print(f"embedding unavailable ({type(exc).__name__}); using keyword mode", file=sys.stderr)
            mode = "keyword"
    with connect() as conn:
        hits = search(conn, args.query, vector, filters, args.k, mode)
        embedded, total = conn.execute(
            "select count(*) filter (where embedding is not null), count(*)"
            " from jobs where status = 'open'").fetchone()
    for position, hit in enumerate(hits, start=1):
        via = "  (via Remote OK)" if hit.source == "remoteok" else ""
        print(f"{position:2}. {hit.title}\n    {hit.company} | {hit.location or 'location not stated'}"
              f" | {hit.level}{via}\n    {hit.apply_url}")
    print(f"\n{len(hits)} results, mode={mode}; {embedded} of {total} open jobs have embeddings")


if __name__ == "__main__":
    main()
