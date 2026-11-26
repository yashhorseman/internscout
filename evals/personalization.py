"""Experiment E6: after one simulated like, do the other relevant postings rise?

    python -m evals.personalization      # development queries only

For each query, each posting graded 2 takes a turn as the liked one. It is removed from both
rankings and from the grades, so nothing is gained by merely returning it.
"""
import json

from app.db import connect
from app.retrieval.personal import personal_search, profile_vector
from evals.common import RESULTS, db_url, load_grades, load_queries, query_vectors
from evals.metrics import paired_difference, score_query

METRICS = ("recall@5", "recall@10", "mrr", "ndcg@10")


def main() -> None:
    queries = [q for q in load_queries() if q["split"] == "dev"]
    vectors, grades = query_vectors(queries), load_grades(extra=True)
    plain_scores, personal_scores, unlabeled, shown, trials = {}, {}, 0, 0, 0
    ungraded = set()
    with connect(db_url()) as conn:
        for query in queries:
            known = grades.get(query["id"], {})
            liked = sorted(j for j, g in known.items() if g == 2)
            if sum(g > 0 for g in known.values()) < 2 or not liked:
                continue
            runs = {"plain": [], "personal": []}
            for job_id in liked:
                rest = {j: g for j, g in known.items() if j != job_id}
                if not any(rest.values()):
                    continue
                trials += 1
                for name, profile in (("plain", None), ("personal", profile_vector(conn, [job_id], []))):
                    hits = personal_search(conn, query["text"], vectors[query["id"]], profile,
                                           query.get("filters"), 11, keywords=query.get("keywords"))
                    ranked = [h.job_id for h in hits if h.job_id != job_id][:10]
                    if name == "personal":
                        unlabeled += sum(j not in known for j in ranked)
                        shown += len(ranked)
                        ungraded.update((query["id"], j) for j in ranked if j not in known)
                    runs[name].append(score_query(ranked, rest))
            if runs["plain"]:
                for name, target in (("plain", plain_scores), ("personal", personal_scores)):
                    target[query["id"]] = {m: sum(r[m] for r in runs[name]) / len(runs[name]) for m in METRICS}

    lines = [f"E6, development queries: {len(plain_scores)} queries, {trials} simulated likes.",
             f"Ungraded postings in the personalised top 10: {unlabeled} of {shown} (counted as not relevant).",
             "", "| Metric | hybrid | hybrid + one like | Difference (95% interval) |", "|---|---|---|---|"]
    differences = {}
    for metric in METRICS:
        a = {q: s[metric] for q, s in plain_scores.items()}
        b = {q: s[metric] for q, s in personal_scores.items()}
        d = differences[metric] = paired_difference(a, b)
        lines.append(f"| {metric} | {sum(a.values()) / len(a):.3f} | {sum(b.values()) / len(b):.3f} | "
                     f"{d['mean']:+.3f} ({d['ci95'][0]:+.3f} to {d['ci95'][1]:+.3f})"
                     f"{'' if d['clear'] else ', not distinguishable'} |")
    text = "\n".join(lines) + "\n"
    (RESULTS / "e6_personalization.md").write_text(text)
    (RESULTS / "e6_ungraded.json").write_text(json.dumps(sorted(ungraded)))
    print(text)


if __name__ == "__main__":
    main()
