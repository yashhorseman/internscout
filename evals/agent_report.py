"""Tables from the agent runs: end-to-end quality, and grounding before and after the checks.

    python -m evals.agent_report
"""
import argparse
import math
from statistics import median

from app.agent import loop, verify
from app.agent.schemas import AgentReply
from app.db import connect
from app.retrieval.search import search
from evals.common import (AGENT_DIR, NO_ANSWER, db_url, load_grades,
                          load_queries, query_vectors, read_jsonl)
from evals.metrics import score_query

UNFINISHED = {"model_busy", "daily_limit", "budget"}


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% interval for a proportion that stays inside 0..1 even for small n."""
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    middle = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (middle - half) / (1 + z * z / n)), min(1.0, (middle + half) / (1 + z * z / n))


def rate(successes: int, n: int) -> str:
    if n == 0:
        return "no cases"
    low, high = wilson(successes, n)
    return f"{successes}/{n} = {successes / n:.0%} ({low:.0%} to {high:.0%})"


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def grounding(conn, runs: list[dict], verdicts: dict, version: str) -> dict:
    """A: the model's first answer, with only unknown ids removed. B: what was shown."""
    recs = []  # (query id, job id, why, evidence, claims)
    unknown = proposed = 0
    for run in runs:
        first = (run["first_answer"] or {}).get("recommendations", [])
        proposed += len(first)
        unknown += sum(r["job_id"] not in run["seen"] for r in first)
        if version == "A":
            recs += [(run["id"], r["job_id"], r["why"], r["evidence"], r["claims"])
                     for r in first if r["job_id"] in run["seen"]]
        else:
            claims = {r["job_id"]: r["claims"] for r in first}
            recs += [(run["id"], c["job_id"], c["why"], c["evidence"], claims.get(c["job_id"], []))
                     for c in run["cards"] if c["evidence"] and c["why"] != loop.NEUTRAL_WHY]
    bad_quote = bad_claim = judged = judged_bad = 0
    for query_id, job_id, why, evidence, claims in recs:
        job = verify.load_job(conn, job_id)
        bad_quote += loop._plain(evidence).strip(" .\"'") not in loop._plain(job["description"])
        if version == "A":
            parsed = AgentReply.model_validate(
                {"message": "", "recommendations": [{"job_id": job_id, "why": why, "evidence": evidence,
                                                     "claims": claims}]})
            bad_claim += bool(verify.failed_claims(job, parsed.recommendations[0].claims))
        verdict = verdicts.get((query_id, job_id, why))
        if verdict is not None:
            judged += 1
            judged_bad += not verdict
    return {"proposed": proposed, "unknown_ids": unknown, "explanations": len(recs),
            "bad_quote": bad_quote, "bad_claim": bad_claim, "judged": judged, "judged_bad": judged_bad}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=loop.PROMPT_VERSION, help="which prompt's runs to report")
    version = parser.parse_args().version
    folder = AGENT_DIR.parent / version
    queries = {q["id"]: q for q in load_queries()}
    impossible = {q["id"] for q in read_jsonl(NO_ANSWER)}
    grades = load_grades(extra=True)
    runs = [r for r in read_jsonl(folder / "runs.jsonl") if r["outcome"] not in UNFINISHED]
    verdicts = {(r["id"], r["job_id"], r["why"]): r["supported"] for r in read_jsonl(folder / "judge.jsonl")}
    total = len(runs)

    scored, unlabeled, ranked_total = {"recommended": [], "searched": []}, 0, 0
    for run in runs:
        known = grades.get(run["id"])
        if run["id"] not in queries or not known:
            continue
        ranked = [c["job_id"] for c in run["cards"]]
        unlabeled += sum(j not in known for j in ranked)
        ranked_total += len(ranked)
        for name, ids in (("recommended", ranked), ("searched", run["found"][:10])):
            scores = score_query(ids, known)
            if scores:
                scored[name].append((run["id"], scores))

    # plain hybrid is scored again here so both sides use the same grades
    baseline = {}
    vectors = query_vectors(list(queries.values()))
    with connect(db_url()) as conn:
        for query in queries.values():
            hits = search(conn, query["text"], vectors[query["id"]], query.get("filters"), 10,
                          keywords=query.get("keywords"))
            scores = score_query([h.job_id for h in hits], grades.get(query["id"], {}))
            if scores:
                baseline[query["id"]] = scores

    lines = [f"Prompt {version}; {total} finished turns "
             f"({len(queries)} benchmark queries and {len(impossible)} with no answer).", "",
             "## End to end", "| Measure | Value |", "|---|---|",
             f"| Turns that used all {loop.MAX_STEPS} tool steps | {rate(sum(r['outcome'] == 'step_limit' or r.get('hit_step_limit', False) for r in runs), total)} |",
             f"| Turns that called search_jobs | {rate(sum(any(t['name'] == 'search_jobs' for t in r['tools']) for r in runs), total)} |",
             f"| First answer rejected (schema, id, quote or claim) | {rate(sum(r['repairs'] > 0 for r in runs), total)} |",
             f"| Ended without a usable answer | {rate(sum(r['outcome'] != 'ok' for r in runs), total)} |",
             f"| Seconds per turn, median / 95th percentile | {median(r['seconds'] for r in runs):.1f} / {percentile([r['seconds'] for r in runs], 0.95):.1f} |",
             f"| Tokens per turn, median (input + output) | {median(r['input_tokens'] + r['output_tokens'] for r in runs):,.0f} |",
             f"| Model calls per turn, median | {median(r['model_calls'] for r in runs):.0f} |",
             "", "## Against plain retrieval (same queries, same grades)",
             "| Ranked list | Split | Queries | Recall@5 | NDCG@10 | Plain hybrid Recall@5 | Plain hybrid NDCG@10 |",
             "|---|---|---|---|---|---|---|"]
    for name, label in (("searched", "What the agent's searches returned"),
                        ("recommended", "What the agent recommended (at most 5)")):
        for split in ("dev", "test"):
            rows = [(q, s) for q, s in scored[name] if q in baseline and queries[q]["split"] == split]
            if not rows:
                continue
            mean = lambda values: sum(values) / len(values)
            lines.append(f"| {label} | {split} | {len(rows)} | {mean([s['recall@5'] for _, s in rows]):.3f} | "
                         f"{mean([s['ndcg@10'] for _, s in rows]):.3f} | "
                         f"{mean([baseline[q]['recall@5'] for q, _ in rows]):.3f} | "
                         f"{mean([baseline[q]['ndcg@10'] for q, _ in rows]):.3f} |")
    lines += ["", f"Recommended jobs with no grade (counted as not relevant): {unlabeled} of {ranked_total}."]

    with connect(db_url()) as conn:
        a, b = grounding(conn, runs, verdicts, "A"), grounding(conn, runs, verdicts, "B")
    lines += ["", "## Grounding: before (A) and after (B) the checks",
              "| Measure | A: first answer | B: shown to the user |", "|---|---|---|",
              f"| H1: ids no tool returned | {rate(a['unknown_ids'], a['proposed'])} | 0 by construction |",
              f"| H2: quote not in the posting | {rate(a['bad_quote'], a['explanations'])} | {rate(b['bad_quote'], b['explanations'])} |",
              f"| H3: a listed claim fails the check | {rate(a['bad_claim'], a['explanations'])} | 0 by construction |",
              f"| H3: AI judge finds an unsupported statement | {rate(a['judged_bad'], a['judged'])} | {rate(b['judged_bad'], b['judged'])} |",
              f"| Explanations | {a['explanations']} | {b['explanations']} |",
              f"| Explanations replaced by a neutral line | | {sum(r['claims_removed'] for r in runs)} |",
              "", "The judge has not been compared with a person yet unless docs/results.md says so."]

    none = [r for r in runs if r["id"] in impossible]
    offered = [r for r in none if any(c["why"] != loop.NEUTRAL_WHY for c in r["cards"])]
    lines += ["", "## H4: queries with no answer in the index",
              f"Turns that still recommended jobs: {rate(len(offered), len(none))}. Whether the message",
              "admits that nothing fits has to be read by a person:", ""]
    lines += [f"- {r['id']} ({len(r['cards'])} cards): {r['message']}" for r in none]

    text = "\n".join(lines) + "\n"
    (folder / "report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
