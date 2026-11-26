"""How well the author's blind grades agree with the AI grades.

    python -m evals.agreement
"""
import sys

from evals.common import QRELS_CHECK, load_grades, read_jsonl


def weighted_kappa(pairs: list[tuple[int, int]], levels: int = 3) -> float:
    """Cohen's kappa with quadratic weights: 0 vs 2 counts four times as much as 0 vs 1.
    1 is full agreement, 0 is what chance would give."""
    n = len(pairs)
    first = [sum(a == g for a, _ in pairs) / n for g in range(levels)]
    second = [sum(b == g for _, b in pairs) / n for g in range(levels)]
    observed = sum((a - b) ** 2 for a, b in pairs) / n
    expected = sum(first[i] * second[j] * (i - j) ** 2 for i in range(levels) for j in range(levels))
    return 1.0 if expected == 0 else 1 - observed / expected


def split_grades(rows: list[dict]) -> tuple[dict, dict]:
    """(blind grades, grades after corrections). A correction is a later row marked
    after_seeing_ai: the grader had seen the AI grade, so it is not part of the blind check."""
    blind, corrected = {}, {}
    for row in rows:
        key = (row["query_id"], row["job_id"])
        if not row.get("after_seeing_ai"):
            blind[key] = row["grade"]
        corrected[key] = row["grade"]
    return blind, corrected


def report(title: str, mine: dict, ai: dict) -> None:
    pairs = [(grade, ai[q][j]) for (q, j), grade in mine.items() if j in ai.get(q, {})]
    print(f"\n== {title} ==")
    print(f"pairs checked: {len(pairs)}")
    print(f"same grade: {sum(a == b for a, b in pairs) / len(pairs):.0%}")
    print(f"same on relevant (1 or 2) vs not (0): {sum((a > 0) == (b > 0) for a, b in pairs) / len(pairs):.0%}")
    print(f"quadratic weighted kappa: {weighted_kappa(pairs):.2f}")
    print("rows: your grade, columns: AI grade\n      0    1    2")
    for a in range(3):
        print(f"{a}  " + "".join(f"{sum(p == (a, b) for p in pairs):>5}" for b in range(3)))


def main() -> None:
    ai = load_grades()
    rows = read_jsonl(QRELS_CHECK)
    if not rows:
        sys.exit("no check grades yet: run python -m evals.label --check 50")
    blind, corrected = split_grades(rows)
    report("blind check (quote this one)", blind, ai)
    if corrected != blind:
        changed = sum(blind[k] != corrected[k] for k in blind)
        report(f"after {changed} corrections made with the AI grades visible (not blind)", corrected, ai)


if __name__ == "__main__":
    main()
