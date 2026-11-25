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


def main() -> None:
    ai = load_grades()
    mine = {(r["query_id"], r["job_id"]): r["grade"] for r in read_jsonl(QRELS_CHECK)}
    pairs = [(grade, ai[q][j]) for (q, j), grade in mine.items() if j in ai.get(q, {})]
    if not pairs:
        sys.exit("no check grades yet: run python -m evals.label --check 50")
    print(f"pairs checked: {len(pairs)}")
    print(f"same grade: {sum(a == b for a, b in pairs) / len(pairs):.0%}")
    print(f"same on relevant (1 or 2) vs not (0): {sum((a > 0) == (b > 0) for a, b in pairs) / len(pairs):.0%}")
    print(f"quadratic weighted kappa: {weighted_kappa(pairs):.2f}")
    print("\nrows: your grade, columns: AI grade\n      0    1    2")
    for a in range(3):
        print(f"{a}  " + "".join(f"{sum(p == (a, b) for p in pairs):>5}" for b in range(3)))


if __name__ == "__main__":
    main()
