"""Judge explanations yourself, without seeing the AI judge's verdict or the checks.

    python -m evals.label_claims            # s supported, p partly, u unsupported, q quit
    python -m evals.label_claims --report   # how well the AI judge agrees with you
"""
import argparse
import json
import random
import sys
import textwrap

from app.db import connect
from evals.common import AGENT_RUNS, HUMAN_CLAIMS, JUDGEMENTS, db_url, read_jsonl
from evals.judge import explanations, posting
from evals.label import read_key

KEYS = {"s": "supported", "p": "partly", "u": "unsupported"}


def report(mine: list[dict], judged: list[dict]) -> str:
    verdicts = {(r["id"], r["job_id"], r["why"]): not r["supported"] for r in judged}
    pairs = [(row["label"] != "supported", verdicts[key]) for row in mine
             if (key := (row["id"], row["job_id"], row["why"])) in verdicts]
    if not pairs:
        return "nothing to compare yet"
    both = sum(h and j for h, j in pairs)
    human, judge = sum(h for h, _ in pairs), sum(j for _, j in pairs)
    lines = [f"labelled and judged: {len(pairs)}",
             f"same verdict: {sum(h == j for h, j in pairs) / len(pairs):.0%}",
             f"unsupported (you, counting partly): {human}; unsupported (judge): {judge}",
             f"judge recall: {both / human:.0%}" if human else "judge recall: no cases",
             f"judge precision: {both / judge:.0%}" if judge else "judge precision: no cases"]
    if human and both / human < 0.75:
        lines.append("The judge misses more than a quarter: do not use it as a gate.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.report:
        print(report(read_jsonl(HUMAN_CLAIMS), read_jsonl(JUDGEMENTS)))
        return
    if not sys.stdin.isatty():
        sys.exit("run this in a terminal window")
    items = explanations(read_jsonl(AGENT_RUNS))
    random.Random(0).shuffle(items)
    done = {(r["id"], r["job_id"], r["why"]) for r in read_jsonl(HUMAN_CLAIMS)}
    todo = [item for item in items if item not in done]
    with connect(db_url()) as conn:
        for number, (query_id, job_id, why) in enumerate(todo, start=len(done) + 1):
            text = posting(conn, job_id)
            full = False
            while True:
                print("\033[2J\033[H", end="")
                print(f"{number} of {len(items)}\n")
                shown = text if full else text[:3000]
                print("\n".join(textwrap.fill(line, 100) for line in shown.splitlines()))
                print(f"\nEXPLANATION: {textwrap.fill(why, 100)}")
                print("\nDoes the posting support every fact in the explanation?")
                print("[s] all of it   [p] partly   [u] no   [m] more/less   [q] quit ", end="", flush=True)
                key = read_key()
                if key != "m":
                    break
                full = not full
            if key == "q":
                break
            if key in KEYS:
                with HUMAN_CLAIMS.open("a") as out:
                    out.write(json.dumps({"id": query_id, "job_id": job_id, "why": why,
                                          "label": KEYS[key]}) + "\n")
    print(f"\n{len(read_jsonl(HUMAN_CLAIMS))} labelled; then: python -m evals.label_claims --report")


if __name__ == "__main__":
    main()
