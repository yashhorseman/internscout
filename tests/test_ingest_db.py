"""New / changed / unchanged / gone, and the guard against wiping the index."""
import json
from pathlib import Path

import httpx
import psycopg
import pytest

from app.db import migrate
from app.ingest.run import ingest_board

BOARD = {"source": "greenhouse", "board": "demo", "company": "Demo"}


def job(i, title="Backend Intern", text="Python and SQL"):
    return {"id": i, "title": title, "location": {"name": "Pune, India"},
            "content": f"<p>{text}</p>", "absolute_url": f"https://example.com/{i}"}


def client_returning(payload, status=200):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=payload))
    return httpx.Client(transport=transport)  # no network in tests


def run(db, jobs, status=200, board=BOARD):
    return ingest_board(db, client_returning({"jobs": jobs}, status), board)


def statuses(db):
    return dict(db.execute("select source_job_id, status from jobs"))


def test_second_identical_run_changes_nothing(db):
    assert run(db, [job(1), job(2)])["new"] == 2
    again = run(db, [job(1), job(2)])
    assert (again["new"], again["changed"], again["closed"]) == (0, 0, 0)


def test_changed_text_marks_the_embedding_stale(db):
    run(db, [job(1)])
    db.execute("update jobs set embedding_stale = false")
    run(db, [job(1)])
    assert db.execute("select embedding_stale from jobs").fetchone()[0] is False
    assert run(db, [job(1, text="Go and Kafka")])["changed"] == 1
    assert db.execute("select embedding_stale from jobs").fetchone()[0] is True


def test_gone_is_closed_and_can_reopen(db):
    run(db, [job(1), job(2)])
    assert run(db, [job(1)])["closed"] == 1
    assert statuses(db) == {"1": "open", "2": "closed"}
    run(db, [job(1), job(2)])
    assert statuses(db) == {"1": "open", "2": "open"}


@pytest.mark.parametrize("status", [404, 500])
def test_a_failing_board_closes_nothing(db, status):
    run(db, [job(1), job(2)])
    result = run(db, [], status=status)
    assert result["error"] and result["closed"] == 0
    assert statuses(db) == {"1": "open", "2": "open"}
    assert db.execute("select count(*) from ingest_runs where error is not null").fetchone()[0] == 1


def test_an_empty_board_closes_nothing(db):
    run(db, [job(1)])
    assert run(db, [])["closed"] == 0
    assert statuses(db) == {"1": "open"}


def test_an_unreadable_item_closes_nothing(db):
    run(db, [job(1), job(2)])
    result = run(db, [job(1), {"id": 2}])
    assert result["error"] and statuses(db)["2"] == "open"


def test_rolling_feed_waits_before_closing(db):
    board = {**BOARD, "expire_after_days": 30}
    run(db, [job(1), job(2)], board=board)
    assert run(db, [job(1)], board=board)["closed"] == 0
    db.execute("update jobs set last_seen_at = now() - interval '31 days' where source_job_id = '2'")
    assert run(db, [job(1)], board=board)["closed"] == 1


def test_database_rejects_unknown_source(db):
    db.execute("insert into companies (name) values ('X')")
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "insert into jobs (source, board, source_job_id, company_id, title, description_text,"
            " apply_url, source_url, content_hash, raw)"
            " values ('foo','b','1',1,'t','d','u','u','h',%s)", (json.dumps({}),))


def test_migrating_twice_does_nothing(db):
    assert migrate(db) == []


def test_improved_rules_reach_unchanged_postings(db):
    run(db, [job(1)])
    db.execute("update jobs set country_code = null")  # as if an older rule had missed it
    assert run(db, [job(1)])["changed"] == 0
    assert db.execute("select country_code from jobs").fetchone()[0] == "IN"
