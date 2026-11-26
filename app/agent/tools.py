"""The four things the model may ask for. None of them has effects outside the session."""
import logging
import time
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.agent import schemas, store
from app.retrieval.personal import personal_search, profile_vector
from app.retrieval.preview import preview, repeated_lines
from app.retrieval.query import embed_query
from app.retrieval.search import FILTER_KEYS, search

log = logging.getLogger(__name__)

SEARCH_MODE = "hybrid"  # to be confirmed by the benchmark
SNIPPET_CHARS = 300
DESCRIPTION_CHARS = 3000


@dataclass
class Context:
    conn: object
    session_id: str
    seen: set[int]                 # ids the model may talk about
    embed: object = embed_query
    found: list[int] = field(default_factory=list)  # ids searched up in this turn, best first


def about_role(conn, jobs: list[tuple[str, str]], chars: int) -> list[str]:
    """For (company, description) pairs: the text with the "about us" opening skipped,
    which would otherwise be most of what the model reads."""
    names = sorted({company for company, _ in jobs})
    rows = conn.execute("select c.name, j.description_text from jobs j join companies c"
                        " on c.id = j.company_id where c.name = any(%s) and j.status = 'open'",
                        (names,)).fetchall()
    repeated = repeated_lines(rows)
    return [preview(text, repeated.get(company, set()), chars) for company, text in jobs]


def search_jobs(ctx: Context, args: schemas.SearchJobs) -> dict:
    filters = {key: getattr(args, key) for key in FILTER_KEYS if getattr(args, key) is not None}
    mode, vector = SEARCH_MODE, None
    try:
        vector = list(ctx.embed(args.query_text))
    except Exception as exc:  # no embedding: keyword search still works
        log.warning("query embedding failed, using keyword search: %s", type(exc).__name__)
        mode = "keyword"
    liked, disliked = store.liked_and_disliked(ctx.conn, ctx.session_id)
    wanted = args.k + len(disliked)  # a disliked job is never shown again, so fetch spares
    profile = profile_vector(ctx.conn, liked, disliked) if vector and (liked or disliked) else None
    if profile is not None:
        hits = personal_search(ctx.conn, args.query_text, vector, profile, filters, wanted,
                               keywords=args.keywords)
    else:
        hits = search(ctx.conn, args.query_text, vector, filters, wanted, mode, keywords=args.keywords)
    hits = [h for h in hits if h.job_id not in disliked][:args.k]
    short = about_role(ctx.conn, [(h.company, h.description) for h in hits], SNIPPET_CHARS) if hits else []
    for hit in hits:
        ctx.seen.add(hit.job_id)
        if hit.job_id not in ctx.found:
            ctx.found.append(hit.job_id)
    return {"jobs": [{"job_id": h.job_id, "title": h.title, "company": h.company,
                      "location": h.location, "level": h.level, "remote": h.is_remote,
                      "snippet": snippet} for h, snippet in zip(hits, short)]}


def get_job(ctx: Context, args: schemas.GetJob) -> dict:
    if args.job_id not in ctx.seen:
        return {"error": "unknown job_id: use an id returned by search_jobs in this conversation"}
    title, company, location, level, remote, text, url = ctx.conn.execute(
        "select j.title, c.name, j.location_raw, j.level, j.is_remote, j.description_text, j.apply_url"
        " from jobs j join companies c on c.id = j.company_id where j.id = %s", (args.job_id,)).fetchone()
    return {"job_id": args.job_id, "title": title, "company": company, "location": location,
            "level": level, "remote": remote, "apply_url": url,
            "description": about_role(ctx.conn, [(company, text)], DESCRIPTION_CHARS)[0]}


def update_profile(ctx: Context, args: schemas.UpdateProfile) -> dict:
    changes = args.model_dump(exclude_none=True)
    return {"profile": store.save_profile(ctx.conn, ctx.session_id, changes)}


def record_feedback(ctx: Context, args: schemas.RecordFeedback) -> dict:
    if args.job_id not in ctx.seen:
        return {"error": "unknown job_id"}
    store.save_feedback(ctx.conn, ctx.session_id, args.job_id, args.signal)
    return {"ok": True}


TOOLS = {
    "search_jobs": (search_jobs, schemas.SearchJobs, "Search open job postings. The only source of jobs."),
    "get_job": (get_job, schemas.GetJob, "Read one posting found earlier, in more detail."),
    "update_profile": (update_profile, schemas.UpdateProfile,
                       "Remember the user's skills, levels, locations or remote preference."),
    "record_feedback": (record_feedback, schemas.RecordFeedback,
                        "Store that the user likes, dislikes or wants to save a job."),
}

DECLARATIONS = [{"name": name, "description": description, "parameters": model.model_json_schema()}
                for name, (_, model, description) in TOOLS.items()]


def execute(ctx: Context, name: str, args: dict) -> dict:
    """Run one tool call. Never raises: problems go back to the model as {"error": ...}."""
    started = time.perf_counter()
    if name not in TOOLS:
        result = {"error": f"there is no tool called {name}"}
    else:
        function, model, _ = TOOLS[name]
        try:
            result = function(ctx, model.model_validate(args))
        except ValidationError as exc:
            result = {"error": "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}"
                                         for e in exc.errors())}
        except Exception:
            log.exception("tool %s failed", name)
            result = {"error": "the tool failed; try different arguments"}
    count = len(result["jobs"]) if "jobs" in result else None
    store.log_tool_call(ctx.conn, ctx.session_id, name, args, count,
                        int((time.perf_counter() - started) * 1000), "error" not in result)
    return result
