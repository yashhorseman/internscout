from app import embed, llm
from app.ingest.models import JobPosting
from app.ingest.store import upsert
from datetime import datetime, timezone


def add_job(db, i, title="Engineer", location="Berlin, Germany"):
    upsert(db, JobPosting(source="greenhouse", board="demo", source_job_id=str(i), company="Demo",
                          title=title, location_raw=location, description_text="text",
                          apply_url="u", source_url="u", raw={}), datetime.now(timezone.utc))


def fake_embed(texts, task):
    return [[1.0] + [0.0] * 767 for _ in texts]


def stale(db):
    return db.execute("select count(*) from jobs where embedding_stale").fetchone()[0]


def test_embeds_every_stale_job_and_logs_the_call(db):
    for i in range(23):
        add_job(db, i)
    result = embed.run(db, embed_fn=fake_embed)
    assert result == {"embedded": 23, "still_stale": 0, "stopped": None}
    assert stale(db) == 0
    assert db.execute("select count(*) from llm_calls where kind='embed' and ok").fetchone()[0] == 3


def test_india_and_early_career_go_first(db):
    add_job(db, 1)
    add_job(db, 2, location="Pune, India")
    add_job(db, 3, title="Software Intern")
    embed.run(db, max_jobs=2, embed_fn=fake_embed)
    left = db.execute("select source_job_id from jobs where embedding_stale").fetchall()
    assert left == [("1",)]


def test_daily_quota_stops_cleanly_and_a_rerun_finishes(db):
    for i in range(15):
        add_job(db, i)
    calls = []

    def quota_after_one(texts, task):
        calls.append(1)
        if len(calls) > 1:
            raise llm.DailyQuotaExhausted("EmbedContentRequestsPerDay limit=1000")
        return fake_embed(texts, task)

    result = embed.run(db, embed_fn=quota_after_one)
    assert result["embedded"] == embed.BATCH_TEXTS
    assert result["still_stale"] == 15 - embed.BATCH_TEXTS
    assert "daily quota" in result["stopped"]
    assert embed.run(db, embed_fn=fake_embed)["still_stale"] == 0


def test_rate_limit_waits_then_retries(db):
    add_job(db, 1)
    waits, calls = [], []

    def limited_once(texts, task):
        calls.append(1)
        if len(calls) == 1:
            raise llm.RateLimited("per minute", retry_after=12)
        return fake_embed(texts, task)

    assert embed.run(db, embed_fn=limited_once, sleep=waits.append)["embedded"] == 1
    assert waits == [12]


def test_limiter_waits_for_the_minute_window():
    now, waits = [0.0], []

    def sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    limiter = embed.MinuteLimiter(100, 1000, clock=lambda: now[0], sleep=sleep)
    limiter.wait_for(1, 600)
    limiter.wait_for(1, 300)
    assert waits == []
    limiter.wait_for(1, 600)
    assert len(waits) == 1 and waits[0] >= 60


def test_quota_errors_are_told_apart():
    def body(quota_id):
        return {"error": {"details": [{"violations": [{"quotaId": quota_id, "quotaValue": "5"}]},
                                      {"retryDelay": "41s"}]}}

    assert isinstance(llm.classify_quota_error(body("RequestsPerDayFree")), llm.DailyQuotaExhausted)
    minute = llm.classify_quota_error(body("RequestsPerMinuteFree"))
    assert isinstance(minute, llm.RateLimited) and minute.retry_after == 41


def test_vectors_are_scaled_to_length_one():
    assert llm.normalize([3.0, 4.0]) == [0.6, 0.8]
