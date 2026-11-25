"""Score a retrieval setting against the labels.

    python -m evals.run_eval --mode hybrid --split dev
    python -m evals.run_eval --compare evals/results/A.json evals/results/B.json
"""
import argparse
import json
import sys
from pathlib import Path

from app.db import connect
from app.retrieval.search import MODES, search
from evals.common import RESULTS, db_url, load_grades, load_queries, query_vectors
from evals.metrics import bootstrap_ci, paired_difference, score_query

METRICS = ("recall@5", "recall@10", "mrr", "ndcg@10")


def evaluate(conn, queries, vectors, grades, **setting) -> dict:
    per_query, no_relevant, unlabeled = {}, [], 0
    for query in queries:
        known = grades.get(query["id"], {})
        hits = search(conn, query["text"], vectors[query["id"]], query.get("filters"), 10,
                      keywords=query.get("keywords"), **setting)
        ranked = [h.job_id for h in hits]
        unlabeled += sum(1 for j in ranked if j not in known)
        scores = score_query(ranked, known)
        if scores is None:
            no_relevant.append(query["id"])
        else:
            per_query[query["id"]] = {**scores, "category": query["category"]}
    return {"setting": setting, "queries_scored": len(per_query), "no_relevant": no_relevant,
            "unlabeled_in_top10": unlabeled, "per_query": per_query,
            "means": {m: sum(s[m] for s in per_query.values()) / len(per_query) for m in METRICS},
            "ci95": {m: bootstrap_ci([s[m] for s in per_query.values()]) for m in METRICS}}


def markdown(result: dict) -> str:
    lines = [f"Setting: {result['setting']}",
             f"Queries scored: {result['queries_scored']}; with nothing relevant: "
             f"{len(result['no_relevant'])}; unlabeled results in top 10: {result['unlabeled_in_top10']}",
             "", "| Metric | Mean | 95% interval |", "|---|---|---|"]
    for metric in METRICS:
        low, high = result["ci95"][metric]
        lines.append(f"| {metric} | {result['means'][metric]:.3f} | {low:.3f} to {high:.3f} |")
    lines += ["", "| Category | n | " + " | ".join(METRICS) + " |", "|---|---|" + "---|" * len(METRICS)]
    categories = sorted({s["category"] for s in result["per_query"].values()})
    for category in categories:
        rows = [s for s in result["per_query"].values() if s["category"] == category]
        cells = " | ".join(f"{sum(r[m] for r in rows) / len(rows):.3f}" for m in METRICS)
        lines.append(f"| {category} | {len(rows)} | {cells} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=MODES, default="hybrid")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--match", choices=["or", "and"], default="or")
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--depth", type=int, default=50)
    parser.add_argument("--final", action="store_true", help="required to look at the test split")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("A", "B"))
    args = parser.parse_args()
    if args.compare:
        a, b = (json.loads(p.read_text())["per_query"] for p in args.compare)
        for metric in METRICS:
            d = paired_difference({q: s[metric] for q, s in a.items()},
                                  {q: s[metric] for q, s in b.items()})
            verdict = "clear difference" if d["clear"] else "not distinguishable"
            print(f"{metric:10} B-A {d['mean']:+.3f}  [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]  {verdict}")
        return
    if args.split == "test" and not args.final:
        sys.exit("tune on dev only. Use --final for the one final test run.")
    queries = [q for q in load_queries() if q["split"] == args.split]
    grades = load_grades()
    unlabeled = [q["id"] for q in queries if q["id"] not in grades]
    if unlabeled:
        sys.exit(f"no labels yet for {len(unlabeled)} queries, e.g. {unlabeled[:3]}")
    with connect(db_url()) as conn:
        result = evaluate(conn, queries, query_vectors(queries), grades, mode=args.mode,
                          match=args.match, rrf_k=args.rrf_k, depth=args.depth)
    RESULTS.mkdir(exist_ok=True)
    name = f"{args.split}_{args.mode}_{args.match}_k{args.rrf_k}_d{args.depth}"
    (RESULTS / f"{name}.json").write_text(json.dumps(result, indent=1))
    (RESULTS / f"{name}.md").write_text(markdown(result))
    print(markdown(result))


if __name__ == "__main__":
    main()
