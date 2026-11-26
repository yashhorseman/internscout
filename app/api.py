"""HTTP API and the one-page UI.

    uvicorn app.api:app --reload
"""
import json
import logging
import secrets
import time
import uuid
from pathlib import Path
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app import context, stats
from app.agent import loop, store
from app.config import settings
from app.db import connect
from app.ratelimit import SlidingWindow

app = FastAPI(title="InternScout")
PAGE = Path(__file__).parent / "static" / "index.html"
limiter = SlidingWindow(settings.rate_limit_messages, settings.rate_limit_seconds)

# one JSON object per line on standard output; message text is never logged
log = logging.getLogger("internscout.requests")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

LOGGED = {("POST", "/sessions"): "new_session", ("POST", "messages"): "message",
          ("POST", "feedback"): "feedback"}


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class Feedback(BaseModel):
    job_id: int
    signal: Literal["like", "dislike", "save", "apply_click"]


def _record(row: dict) -> None:
    try:
        with connect() as conn:
            conn.execute(
                "insert into requests (request_id, route, status, latency_ms, session_id, outcome,"
                " repairs, claims_removed, is_test) values (%(request_id)s, %(route)s, %(status)s,"
                " %(latency_ms)s, (select id from sessions where id = %(session_id)s::uuid),"
                " %(outcome)s, %(repairs)s, %(claims_removed)s,"
                " coalesce((select is_test from sessions where id = %(session_id)s::uuid), %(is_test)s))",
                row)
    except Exception as exc:  # losing a statistics row must not fail the request
        logging.getLogger(__name__).warning("could not record the request: %s", type(exc).__name__)


@app.middleware("http")
async def track(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    context.request_id.set(request_id)
    request.state.facts = {}
    started, status = time.perf_counter(), 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        path = request.url.path
        route = LOGGED.get((request.method, path)) or LOGGED.get((request.method, path.rsplit("/", 1)[-1]))
        facts = request.state.facts
        entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "level": "ERROR" if status >= 500 else "INFO", "request_id": request_id,
                 "method": request.method, "route": route or path, "status": status,
                 "latency_ms": int((time.perf_counter() - started) * 1000), **facts}
        log.info(json.dumps(entry))
        if route:
            await run_in_threadpool(_record, {
                "request_id": request_id, "route": route, "status": status,
                "latency_ms": entry["latency_ms"], "session_id": facts.get("session_id"),
                "outcome": facts.get("outcome"), "repairs": facts.get("repairs"),
                "claims_removed": facts.get("claims_removed"),
                "is_test": settings.mark_sessions_as_test})


@app.exception_handler(psycopg.OperationalError)
def database_down(request: Request, exc: psycopg.OperationalError):
    logging.getLogger(__name__).error("database unavailable: %s", type(exc).__name__)
    return JSONResponse({"detail": "the database is unavailable, try again shortly"}, status_code=503)


def db():
    with connect() as conn:
        yield conn


def session(session_id: UUID, request: Request, conn=Depends(db)) -> str:
    if not store.session_exists(conn, str(session_id)):
        raise HTTPException(404, "unknown session")
    request.state.facts["session_id"] = str(session_id)
    return str(session_id)


@app.get("/")
def page():
    return FileResponse(PAGE)


@app.get("/health")
def health(conn=Depends(db)):
    conn.execute("select 1")
    return {"ok": True}


@app.post("/sessions")
def new_session(request: Request, conn=Depends(db)):
    session_id = store.create_session(conn, settings.mark_sessions_as_test)
    request.state.facts["session_id"] = session_id
    return {"session_id": session_id}


@app.post("/sessions/{session_id}/messages")
def message(body: Text, request: Request, session_id: str = Depends(session), conn=Depends(db)):
    address = request.client.host if request.client else "unknown"
    if not limiter.allow(f"session:{session_id}", f"address:{address}"):
        raise HTTPException(429, "too many messages, wait a few minutes")
    reply = loop.run_turn(conn, session_id, body.text)
    request.state.facts.update({key: reply[key] for key in ("outcome", "repairs", "claims_removed")
                                if key in reply})
    return reply


@app.post("/sessions/{session_id}/feedback")
def feedback(body: Feedback, session_id: str = Depends(session), conn=Depends(db)):
    if body.job_id not in store.seen_job_ids(conn, session_id):
        raise HTTPException(400, "that job was not shown in this session")
    store.save_feedback(conn, session_id, body.job_id, body.signal)
    return {"ok": True}


@app.get("/jobs/{job_id}")
def job(job_id: int, conn=Depends(db)):
    row = conn.execute(
        "select j.title, c.name, j.location_raw, j.level, j.description_text, j.apply_url, j.source,"
        " j.source_url, j.status from jobs j join companies c on c.id = j.company_id where j.id = %s",
        (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such job")
    keys = ("title", "company", "location", "level", "description", "apply_url", "source",
            "source_url", "status")
    return {"job_id": job_id, **dict(zip(keys, row))}


@app.get("/admin/stats")
def admin_stats(authorization: str = Header(""), conn=Depends(db)):
    if not settings.admin_token:
        raise HTTPException(404, "not found")
    if not secrets.compare_digest(authorization.encode(), f"Bearer {settings.admin_token}".encode()):
        raise HTTPException(401, "bad token")
    return stats.collect(conn)
