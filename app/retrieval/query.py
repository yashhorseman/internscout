"""Query embeddings, cached so a repeated query costs no quota."""
from functools import lru_cache

from app import llm


@lru_cache(maxsize=1024)
def embed_query(text: str) -> tuple[float, ...]:
    return tuple(llm.embed([text], llm.TASK_QUERY)[0])
