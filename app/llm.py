"""The only file that talks to the LLM provider. Nothing else imports its SDK."""
import math
import re

from google import genai
from google.genai import errors, types

from app.config import settings

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIMS = 768
TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"  # for postings
TASK_QUERY = "RETRIEVAL_QUERY"        # for what the user types

_client: genai.Client | None = None


class RateLimited(Exception):
    """Too many requests right now; try again after `retry_after` seconds."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class DailyQuotaExhausted(Exception):
    """Today's free quota is used up; waiting a few seconds will not help."""


def client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is empty. Put it in .env")
        _client = genai.Client(api_key=settings.gemini_api_key,
                               http_options=types.HttpOptions(timeout=30_000))
    return _client


def classify_quota_error(details) -> Exception:
    """Turn the provider's 429 body into one of our two quota errors."""
    error = (details or {}).get("error", {}) if isinstance(details, dict) else {}
    quota_ids, retry_after = [], None
    for item in error.get("details", []):
        quota_ids += [v.get("quotaId", "") + " limit=" + str(v.get("quotaValue"))
                      for v in item.get("violations", [])]
        match = re.fullmatch(r"([\d.]+)s", str(item.get("retryDelay", "")))
        if match:
            retry_after = float(match.group(1))
    message = "; ".join(quota_ids) or error.get("message", "quota exceeded")
    if any("PerDay" in q for q in quota_ids):
        return DailyQuotaExhausted(message)
    return RateLimited(message, retry_after)


def normalize(vector: list[float]) -> list[float]:
    """Scale to length 1. Needed because 768 is not the model's native size."""
    length = math.sqrt(sum(x * x for x in vector))
    return [x / length for x in vector] if length else vector


def embed(texts: list[str], task: str) -> list[list[float]]:
    try:
        response = client().models.embed_content(
            model=EMBED_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=EMBED_DIMS),
        )
    except errors.APIError as exc:
        if exc.code == 429:
            raise classify_quota_error(exc.details) from exc
        raise
    vectors = [normalize(e.values) for e in response.embeddings]
    if len(vectors) != len(texts):
        raise RuntimeError(f"asked for {len(texts)} embeddings, got {len(vectors)}")
    return vectors


def count_tokens(text: str) -> int:
    return client().models.count_tokens(model=EMBED_MODEL, contents=text).total_tokens
