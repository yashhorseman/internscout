"""HTTP API and the one-page UI.

    uvicorn app.api:app --reload
"""
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent import loop, store
from app.db import connect

app = FastAPI(title="InternScout")
PAGE = Path(__file__).parent / "static" / "index.html"


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class Feedback(BaseModel):
    job_id: int
    signal: Literal["like", "dislike", "save"]


def db():
    with connect() as conn:
        yield conn


def session(session_id: UUID, conn=Depends(db)) -> str:
    if not store.session_exists(conn, str(session_id)):
        raise HTTPException(404, "unknown session")
    return str(session_id)


@app.get("/")
def page():
    return FileResponse(PAGE)


@app.get("/health")
def health(conn=Depends(db)):
    conn.execute("select 1")
    return {"ok": True}


@app.post("/sessions")
def new_session(conn=Depends(db)):
    return {"session_id": store.create_session(conn)}


@app.post("/sessions/{session_id}/messages")
def message(body: Text, session_id: str = Depends(session), conn=Depends(db)):
    return loop.run_turn(conn, session_id, body.text)


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
