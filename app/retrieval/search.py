"""One search function with four interchangeable modes, so they compare fairly."""
import re
from dataclasses import dataclass

import psycopg

MODES = ("keyword", "semantic", "hybrid", "hybrid_rerank")
FILTER_KEYS = ("company", "country_code", "is_remote", "level")

# Values are always passed as parameters; this text never contains user input.
FILTER_SQL = """
  j.status = 'open'
  and (%(level)s::text is null or j.level = %(level)s)
  and (%(country_code)s::text is null or j.country_code = %(country_code)s)
  and (%(is_remote)s::boolean is null or j.is_remote = %(is_remote)s)
  and (%(company)s::text is null or j.company_id in
       (select id from companies where lower(name) = lower(%(company)s)))
"""

LEXICAL_SQL = """
  select j.id, ts_rank_cd(j.fts, q) as score
  from jobs j, {query_function}('english', %(tsq)s) q
  where j.fts @@ q and """ + FILTER_SQL + """
  order by score desc, j.id
  limit %(depth)s
"""

# ORDER BY the distance alone, or the HNSW index cannot be used.
SEMANTIC_SQL = """
  select j.id, j.embedding <=> %(qv)s::vector as distance
  from jobs j
  where j.embedding is not null and """ + FILTER_SQL + """
  order by distance
  limit %(depth)s
"""


@dataclass
class Hit:
    job_id: int
    score: float
    title: str = ""
    company: str = ""
    location: str | None = None
    level: str = "unknown"
    is_remote: bool | None = None
    description: str = ""
    apply_url: str = ""
    source: str = ""
    source_url: str = ""


def keyword_terms(words: list[str]) -> list[str]:
    """Keep letters, digits, + # . so nothing can break the tsquery syntax."""
    terms = []
    for word in words:
        for token in re.sub(r"[^\w+#.]|_", " ", word).split():
            token = token.strip(".")
            if any(ch.isalnum() for ch in token) and token.lower() not in terms:
                terms.append(token.lower())
    return terms


def _lexical(conn, params, query_text, keywords, match) -> list[int]:
    if match == "or":
        terms = keyword_terms(keywords or query_text.split())
        function, tsq = "to_tsquery", " | ".join(terms)
    else:  # "and": every word must appear (experiment E1)
        function = "websearch_to_tsquery"
        tsq = " ".join(keywords) if keywords else query_text
    if not tsq.strip():
        return []
    sql = LEXICAL_SQL.format(query_function=function)
    return [row[0] for row in conn.execute(sql, {**params, "tsq": tsq})]


def _semantic(conn, params, query_vec) -> list[int]:
    with conn.transaction():
        # with an approximate index, filters apply after the scan; iterate until full
        conn.execute("set local hnsw.iterative_scan = relaxed_order")
        conn.execute("set local hnsw.ef_search = 100")
        rows = conn.execute(SEMANTIC_SQL, {**params, "qv": str(query_vec)}).fetchall()
    return [job_id for job_id, _ in sorted(rows, key=lambda r: (r[1], r[0]))]


def rrf(ranked_lists: list[list[int]], rrf_k: int = 60) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: each list adds 1 / (rrf_k + rank) to a result."""
    scores: dict[int, float] = {}
    for ids in ranked_lists:
        for rank, job_id in enumerate(ids, start=1):
            scores[job_id] = scores.get(job_id, 0.0) + 1.0 / (rrf_k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def _load(conn, scored: list[tuple[int, float]]) -> list[Hit]:
    if not scored:
        return []
    rows = conn.execute(
        "select j.id, j.title, c.name, j.location_raw, j.level, j.is_remote, j.description_text,"
        " j.apply_url, j.source, j.source_url"
        " from jobs j join companies c on c.id = j.company_id where j.id = any(%s)",
        ([job_id for job_id, _ in scored],),
    )
    by_id = {row[0]: row[1:] for row in rows}
    return [Hit(job_id, score, *by_id[job_id]) for job_id, score in scored]


def search(conn: psycopg.Connection, query_text: str, query_vec: list[float] | None = None,
           filters: dict | None = None, k: int = 10, mode: str = "hybrid", *,
           keywords: list[str] | None = None, match: str = "or", rrf_k: int = 60,
           depth: int = 50, scorer=None) -> list[Hit]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    unknown = set(filters or {}) - set(FILTER_KEYS)
    if unknown:
        raise ValueError(f"unknown filters: {sorted(unknown)}")
    if mode != "keyword" and query_vec is None:
        raise ValueError(f"mode {mode!r} needs a query vector")
    params = {key: (filters or {}).get(key) for key in FILTER_KEYS}
    params["depth"] = max(depth, k)

    lists = []
    if mode != "semantic":
        lists.append(_lexical(conn, params, query_text, keywords, match))
    if mode != "keyword":
        lists.append(_semantic(conn, params, query_vec))
    scored = rrf(lists, rrf_k)  # with one list this just keeps its order

    if mode != "hybrid_rerank":
        return _load(conn, scored[:k])
    if scorer is None:
        from app.retrieval.rerank import cross_encoder_scores as scorer
    candidates = _load(conn, scored[:depth])
    if not candidates:
        return []
    passages = [f"{h.title} at {h.company}. {h.description[:1000]}" for h in candidates]
    for hit, score in zip(candidates, scorer(query_text, passages)):
        hit.score = float(score)
    return sorted(candidates, key=lambda h: (-h.score, h.job_id))[:k]
