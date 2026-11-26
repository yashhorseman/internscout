"""Limits, request logs, statistics and deletion."""
import pytest
from fastapi.testclient import TestClient

from app import admin, api, llm
from app.agent import loop, store
from app.ratelimit import SlidingWindow


def test_sliding_window():
    now = [0.0]
    window = SlidingWindow(2, 10, clock=lambda: now[0])
    assert window.allow("s:a", "ip:1") and window.allow("s:a", "ip:1")
    assert not window.allow("s:a", "ip:1")
    assert not window.allow("s:b", "ip:1")  # same address, new session: still limited
    assert window.allow("s:b", "ip:2")      # and the refusal did not count against s:b
    now[0] = 11
    assert window.allow("s:a", "ip:1")


@pytest.fixture
def client(db, test_db_url, monkeypatch):
    monkeypatch.setattr(api.settings, "database_url", test_db_url)
    monkeypatch.setattr(api.settings, "admin_token", "secret-token")
    monkeypatch.setattr(api, "limiter", SlidingWindow(2, 600))
    monkeypatch.setattr(loop, "run_turn", lambda conn, sid, text: {
        "message": "ok", "cards": [], "outcome": "model_busy", "repairs": 0, "claims_removed": 0})
    return TestClient(api.app, raise_server_exceptions=False)


def test_requests_are_limited_logged_and_counted(client, db):
    session = client.post("/sessions").json()["session_id"]
    codes = [client.post(f"/sessions/{session}/messages", json={"text": "hi"}).status_code
             for _ in range(3)]
    assert codes == [200, 200, 429]
    assert client.post(f"/sessions/{session}/messages", json={"text": "x" * 1001}).status_code == 422
    rows = db.execute("select route, status, outcome from requests order by id").fetchall()
    assert rows[:4] == [("new_session", 200, None), ("message", 200, "model_busy"),
                        ("message", 200, "model_busy"), ("message", 429, None)]

    assert client.get("/admin/stats").status_code == 401
    stats = client.get("/admin/stats", headers={"Authorization": "Bearer secret-token"}).json()
    day = stats["last_24_hours"]["requests"]
    assert (day["turns"], day["degraded_turns"], day["rate_limited"], day["active_sessions"]) == (2, 2, 1, 1)


def test_stats_are_off_without_a_token(client, monkeypatch):
    monkeypatch.setattr(api.settings, "admin_token", "")
    assert client.get("/admin/stats").status_code == 404


def test_database_down_gives_503(client, monkeypatch):
    monkeypatch.setattr(api.settings, "database_url", "postgresql://postgres:x@127.0.0.1:1/none")
    assert client.get("/health").status_code == 503


def test_deleting_a_session_removes_what_the_user_typed(db):
    session = store.create_session(db)
    store.save_message(db, session, "user", {"text": "private words"})
    store.log_tool_call(db, session, "search_jobs", {"query_text": "private words"}, 0, 1, True)
    store.log_llm_call(db, session, "m", 1, False, "v2", error=str(llm.ModelUnavailable("503")))
    assert admin.purge(db, days=1) == 0  # it is new
    assert admin.delete_session(db, session) == 1
    for table, expected in (("messages", 0), ("tool_calls", 0), ("sessions", 0)):
        assert db.execute(f"select count(*) from {table}").fetchone()[0] == expected
