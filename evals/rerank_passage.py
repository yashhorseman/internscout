"""Does the re-ranker do better when it reads about the role, not the company introduction?

    python -m evals.rerank_passage      # development queries only
"""
import json

from app.agent.tools import about_role
from app.db import connect
from app.retrieval.rerank import cross_encoder_scores
from app.retrieval.search import search
from evals.common import RESULTS, db_url, load_grades, load_queries, query_vectors
from evals.metrics import paired_difference, score_query

METRICS = ("recall@5", "recall@10", "mrr", "ndcg@10")


def rank(conn, query, vector) -> list[int]:
    candidates = search(conn, query["text"], vector, query.get("filters"), 50, "hybrid",
                        keywords=query.get("keywords"))
    if not candidates:
        return []
    texts = about_role(conn, [(h.company, h.description) for h in candidates], 1000)
    passages = [f"{h.title} at {h.company}. {text[:1000]}" for h, text in zip(candidates, texts)]
    scores = cross_encoder_scores(query["text"], passages)
    ordered = sorted(zip(candidates, scores), key=lambda pair: (-pair[1], pair[0].job_id))
    return [hit.job_id for hit, _ in ordered[:10]]


def main() -> None:
    queries = [q for q in load_queries() if q["split"] == "dev"]
    vectors, grades = query_vectors(queries), load_grades(extra=True)
    scores, ungraded = {}, []
    baseline = {"hybrid": {}, "hybrid_rerank": {}}
    with connect(db_url()) as conn:
        for query in queries:
            ranked = rank(conn, query, vectors[query["id"]])
            known = grades.get(query["id"], {})
            ungraded += [(query["id"], j) for j in ranked if j not in known]
            result = score_query(ranked, known)
            if not result:
                continue
            scores[query["id"]] = result
            # the other arms are scored again so that all three use the same grades
            for mode, target in baseline.items():
                hits = search(conn, query["text"], vectors[query["id"]], query.get("filters"), 10,
                              mode, keywords=query.get("keywords"))
                target[query["id"]] = score_query([h.job_id for h in hits], known)
    lines = [f"Development queries scored: {len(scores)}. Ungraded postings in the new top 10: "
             f"{len(ungraded)} (counted as not relevant).", "",
             "| Metric | hybrid | re-ranker, first 1,000 chars | re-ranker, role text | Role text minus first chars |",
             "|---|---|---|---|---|"]
    for metric in METRICS:
        new = {q: s[metric] for q, s in scores.items()}
        old = {q: baseline["hybrid_rerank"][q][metric] for q in new}
        plain = {q: baseline["hybrid"][q][metric] for q in new}
        d = paired_difference(old, new)
        mean = lambda values: sum(values.values()) / len(values)
        lines.append(f"| {metric} | {mean(plain):.3f} | {mean(old):.3f} | {mean(new):.3f} | {d['mean']:+.3f} "
                     f"({d['ci95'][0]:+.3f} to {d['ci95'][1]:+.3f}){'' if d['clear'] else ', not distinguishable'} |")
    text = "\n".join(lines) + "\n"
    (RESULTS / "rerank_passage.md").write_text(text)
    (RESULTS / "rerank_passage_ungraded.json").write_text(json.dumps(ungraded))
    print(text)


if __name__ == "__main__":
    main()
