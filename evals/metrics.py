"""Retrieval metrics. A grade of 1 or 2 counts as relevant; NDCG uses the grade."""
import math
import random


def recall_at(ranked: list[int], grades: dict[int, int], k: int) -> float:
    relevant = {j for j, g in grades.items() if g > 0}
    return len(relevant & set(ranked[:k])) / len(relevant)


def reciprocal_rank(ranked: list[int], grades: dict[int, int]) -> float:
    for position, job_id in enumerate(ranked, start=1):
        if grades.get(job_id, 0) > 0:
            return 1 / position
    return 0.0


def _dcg(gains: list[int]) -> float:
    return sum((2 ** g - 1) / math.log2(i + 1) for i, g in enumerate(gains, start=1))


def ndcg_at(ranked: list[int], grades: dict[int, int], k: int = 10) -> float:
    ideal = _dcg(sorted(grades.values(), reverse=True)[:k])
    return _dcg([grades.get(j, 0) for j in ranked[:k]]) / ideal


def score_query(ranked: list[int], grades: dict[int, int]) -> dict | None:
    """None when nothing is relevant: such queries are counted separately."""
    if not any(g > 0 for g in grades.values()):
        return None
    return {"recall@5": recall_at(ranked, grades, 5), "recall@10": recall_at(ranked, grades, 10),
            "mrr": reciprocal_rank(ranked, grades), "ndcg@10": ndcg_at(ranked, grades, 10)}


def bootstrap_ci(values: list[float], samples: int = 1000, seed: int = 0) -> tuple[float, float]:
    """95% interval for the mean, resampling queries with replacement."""
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(samples))
    return means[int(0.025 * samples)], means[int(0.975 * samples) - 1]


def paired_difference(a: dict[str, float], b: dict[str, float]) -> dict:
    """b minus a on the queries both have. 'clear' means the interval excludes zero."""
    shared = sorted(set(a) & set(b))
    differences = [b[q] - a[q] for q in shared]
    low, high = bootstrap_ci(differences)
    return {"n": len(shared), "mean": sum(differences) / len(differences),
            "ci95": [low, high], "clear": low > 0 or high < 0}
