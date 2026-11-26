"""Likes and dislikes as a third ranked list in the fusion (a simple relevance-feedback idea)."""
from app.llm import normalize
from app.retrieval.search import FILTER_KEYS, Hit, _lexical, _load, _semantic, rrf

DISLIKE_WEIGHT = 0.5


def profile_vector(conn, liked: list[int], disliked: list[int]) -> list[float] | None:
    """Average of the liked postings' vectors minus half the average of the disliked ones."""
    def mean(ids):
        rows = conn.execute("select embedding::real[] from jobs where id = any(%s)"
                            " and embedding is not null", (ids,)).fetchall()
        return [sum(column) / len(rows) for column in zip(*(r[0] for r in rows))] if rows else None

    up, down = mean(liked), mean(disliked)
    if up is None and down is None:
        return None
    size = len(up or down)
    return normalize([(up[i] if up else 0.0) - DISLIKE_WEIGHT * (down[i] if down else 0.0)
                      for i in range(size)])


def personal_search(conn, query_text, query_vec, profile_vec, filters=None, k=10, *,
                    keywords=None, rrf_k=60, depth=50) -> list[Hit]:
    """Hybrid search; with a profile, its nearest postings (under the same filters) join the fusion.
    With no profile the result equals plain hybrid."""
    params = {key: (filters or {}).get(key) for key in FILTER_KEYS}
    params["depth"] = max(depth, k)
    lists = [_lexical(conn, params, query_text, keywords, "or"), _semantic(conn, params, query_vec)]
    if profile_vec is not None:
        lists.append(_semantic(conn, params, profile_vec))
    return _load(conn, rrf(lists, rrf_k)[:k])
