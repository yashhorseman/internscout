"""Paths and loading shared by the eval scripts."""
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from app.agent.loop import PROMPT_VERSION
from app.config import settings

HERE = Path(__file__).parent
QUERIES = HERE / "queries.jsonl"
QRELS = HERE / "qrels.jsonl"
QRELS_CHECK = HERE / "qrels_check.jsonl"  # the author's blind re-grades
EARLIER_CHECKS = HERE / "qrels_check_round1.jsonl"  # already seen: never sampled again
# grades for postings first surfaced by later experiments; kept apart so the benchmark stays frozen
QRELS_EXTRA = HERE / "qrels_extra.jsonl"
POOL = HERE / "pool.json"
VECTORS = HERE / "query_vectors.json"
RESULTS = HERE / "results"
EVAL_DB = "internscout_eval"
NO_ANSWER = HERE / "no_answer.jsonl"  # requests the index cannot satisfy, each with a proof query
AGENT_DIR = RESULTS / "agent" / PROMPT_VERSION  # one folder of results per prompt version
AGENT_RUNS = AGENT_DIR / "runs.jsonl"
JUDGEMENTS = AGENT_DIR / "judge.jsonl"
CONVERSATIONS = AGENT_DIR / "conversations.jsonl"
HUMAN_CLAIMS = HERE / "hallucination_labels.jsonl"


def db_url(name: str = EVAL_DB) -> str:
    return urlunsplit(urlsplit(settings.database_url)._replace(path=f"/{name}"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_queries() -> list[dict]:
    return read_jsonl(QUERIES)


def load_grades(extra: bool = False) -> dict[str, dict[int, int]]:
    """{query id: {job id: grade}}. A later line overrides an earlier one.
    `extra` adds the later grades; use it only when every arm of a comparison gets them."""
    grades: dict[str, dict[int, int]] = {}
    for row in read_jsonl(QRELS) + (read_jsonl(QRELS_EXTRA) if extra else []):
        grades.setdefault(row["query_id"], {})[row["job_id"]] = row["grade"]
    return grades


def query_vectors(queries: list[dict]) -> dict[str, list[float]]:
    """Embed each query once and keep it on disk, so runs repeat exactly."""
    from app import llm

    cache = json.loads(VECTORS.read_text()) if VECTORS.exists() else {}
    missing = sorted({q["text"] for q in queries} - set(cache))
    for start in range(0, len(missing), 20):
        batch = missing[start:start + 20]
        cache.update(zip(batch, llm.embed(batch, llm.TASK_QUERY)))
        VECTORS.write_text(json.dumps(cache))
    return {q["id"]: cache[q["text"]] for q in queries}
