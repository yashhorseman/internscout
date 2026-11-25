"""Cross-encoder re-ranker (Apache-2.0). Heavy: needs requirements-rerank.txt."""
from functools import lru_cache

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(MODEL_NAME)


def cross_encoder_scores(query: str, passages: list[str]) -> list[float]:
    return [float(s) for s in _model().predict([(query, p) for p in passages])]
