import math

import pytest

from evals.metrics import (bootstrap_ci, ndcg_at, paired_difference, recall_at, reciprocal_rank,
                           score_query)

GRADES = {1: 2, 2: 1, 3: 0, 4: 1}


def test_recall_and_reciprocal_rank():
    assert recall_at([3, 1, 9, 2], GRADES, 2) == pytest.approx(1 / 3)
    assert recall_at([3, 1, 9, 2], GRADES, 5) == pytest.approx(2 / 3)
    assert reciprocal_rank([3, 1], GRADES) == 0.5
    assert reciprocal_rank([3, 9], GRADES) == 0.0


def test_ndcg_by_hand():
    dcg = 1 / math.log2(2) + 3 / math.log2(3)                      # grades 1 then 2
    ideal = 3 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)  # 2, 1, 1
    assert ndcg_at([2, 1], GRADES) == pytest.approx(dcg / ideal)
    assert ndcg_at([1, 2, 4], GRADES) == pytest.approx(1.0)


def test_a_query_with_nothing_relevant_is_not_scored():
    assert score_query([1, 2], {1: 0, 2: 0}) is None


def test_bootstrap_repeats_exactly():
    values = [0.1, 0.9, 0.5, 0.7, 0.3]
    assert bootstrap_ci(values) == bootstrap_ci(values)


def test_paired_difference():
    a = {f"q{i}": 0.2 for i in range(20)}
    assert paired_difference(a, {q: v + 0.3 for q, v in a.items()})["clear"]
    assert not paired_difference(a, a)["clear"]
