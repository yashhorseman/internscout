"""Paths and loading shared by the eval scripts."""
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from app.config import settings

HERE = Path(__file__).parent
QUERIES = HERE / "queries.jsonl"
QRELS = HERE / "qrels.jsonl"
POOL = HERE / "pool.json"
VECTORS = HERE / "query_vectors.json"
RESULTS = HERE / "results"
EVAL_DB = "internscout_eval"


def db_url(name: str = EVAL_DB) -> str:
    return urlunsplit(urlsplit(settings.database_url)._replace(path=f"/{name}"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_queries() -> list[dict]:
    return read_jsonl(QUERIES)


def load_grades() -> dict[str, dict[int, int]]:
    """{query id: {job id: grade}}. A later line overrides an earlier one."""
    grades: dict[str, dict[int, int]] = {}
    for row in read_jsonl(QRELS):
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
