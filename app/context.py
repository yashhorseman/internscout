"""The id of the request being served, so every log row can be traced back to it."""
from contextvars import ContextVar

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
