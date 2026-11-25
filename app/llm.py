"""The only file that talks to the LLM provider. Nothing else imports its SDK."""
import math
import re
import time
from dataclasses import dataclass, field

import httpx
import httpx2
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


class ModelUnavailable(Exception):
    """The provider was overloaded or timed out on every attempt."""


@dataclass
class ToolCall:
    name: str
    args: dict
    id: str | None = None


@dataclass
class Message:
    role: str                    # "user", "assistant" or "tool"
    text: str = ""
    tool_name: str = ""          # tool messages only
    call_id: str | None = None   # tool messages only
    result: dict | None = None   # tool messages only
    raw: object = None           # the provider's own object, replayed unchanged


@dataclass
class LLMResult:
    message: Message
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def text(self) -> str:
        return self.message.text


GENERATE_ATTEMPTS = 4
MAX_RATE_LIMIT_WAIT = 30  # seconds; a longer wait is not worth it with a user waiting


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


def _contents(messages: list[Message]) -> list:
    """Our messages in the provider's shape. Results of one step go back together."""
    contents, results = [], []
    for message in messages:
        if message.role == "tool":
            results.append(types.Part(function_response=types.FunctionResponse(
                name=message.tool_name, id=message.call_id, response=message.result)))
            continue
        if results:
            contents.append(types.Content(role="user", parts=results))
            results = []
        if message.raw is not None:  # keeps the signature the model expects back
            contents.append(message.raw)
        else:
            role = "model" if message.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=message.text)]))
    if results:
        contents.append(types.Content(role="user", parts=results))
    return contents


def generate(messages: list[Message], *, system: str, tools: list[dict] | None = None,
             schema: dict | None = None, sleep=time.sleep) -> LLMResult:
    """One chat call. Give `tools` to let the model call them, or `schema` for JSON output."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    if tools:
        config.tools = [types.Tool(function_declarations=[types.FunctionDeclaration(
            name=t["name"], description=t["description"], parameters_json_schema=t["parameters"])
            for t in tools])]
    if schema:
        config.response_mime_type = "application/json"
        config.response_json_schema = schema

    contents = _contents(messages)
    for attempt in range(1, GENERATE_ATTEMPTS + 1):
        wait = 2 ** attempt
        try:
            response = client().models.generate_content(
                model=settings.chat_model, contents=contents, config=config)
            break
        except errors.APIError as exc:
            if exc.code == 429:
                problem = classify_quota_error(exc.details)
                wait = getattr(problem, "retry_after", None) or wait
                if isinstance(problem, DailyQuotaExhausted) or wait > MAX_RATE_LIMIT_WAIT:
                    raise problem from exc
            elif exc.code >= 500:
                problem = ModelUnavailable(f"{exc.code} from the model provider")
            else:
                raise
        except (httpx.TransportError, httpx2.TransportError) as exc:
            problem = ModelUnavailable(type(exc).__name__)
        if attempt == GENERATE_ATTEMPTS:
            raise problem
        sleep(wait)

    content = response.candidates[0].content if response.candidates else None
    parts = (content.parts if content else None) or []
    calls = [ToolCall(p.function_call.name, dict(p.function_call.args or {}), p.function_call.id)
             for p in parts if p.function_call]
    text = "".join(p.text for p in parts if p.text and not p.thought)
    usage = response.usage_metadata
    return LLMResult(
        Message("assistant", text, raw=content if calls else None), calls, settings.chat_model,
        usage.prompt_token_count if usage else None,
        ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else None,
    )
