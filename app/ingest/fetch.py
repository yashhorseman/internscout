"""Polite HTTP: timeout, honest User-Agent, retries only where retrying can help."""
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings


def _worth_retrying(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):  # includes timeouts
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


def make_client() -> httpx.Client:
    return httpx.Client(timeout=20, headers={"User-Agent": settings.user_agent}, follow_redirects=True)


@retry(retry=retry_if_exception(_worth_retrying), stop=stop_after_attempt(3),
       wait=wait_exponential(min=1, max=10), reraise=True)
def get_json(client: httpx.Client, url: str):
    response = client.get(url)
    response.raise_for_status()
    return response.json()
