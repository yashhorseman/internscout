"""The mappers, against real responses saved on 2026-11-25."""
import json
from pathlib import Path

from app.ingest import greenhouse, lever, remoteok

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def test_greenhouse():
    board = {"board": "groww", "company": "Groww"}
    item = greenhouse.items(load("greenhouse_sample.json"))[0]
    job = greenhouse.to_posting(item, board)
    assert job.source_job_id == str(item["id"])
    assert job.title == item["title"].strip()
    assert "India" in job.location_raw
    assert job.is_remote is None
    assert "<" not in job.description_text[:500]
    assert "&lt;" not in job.description_text
    assert job.posted_at is not None


def test_lever_includes_requirement_lists():
    board = {"board": "meesho", "company": "Meesho"}
    item = lever.items(load("lever_sample.json"))[0]
    job = lever.to_posting(item, board)
    assert job.company == "Meesho"
    assert job.country_code == "IN"
    assert job.is_remote is False
    assert item["lists"][0]["text"].strip() in job.description_text
    assert "\n- " in job.description_text


def test_remoteok_skips_the_terms_notice_and_links_back():
    entries = remoteok.items(load("remoteok_sample.json"))
    assert len(entries) == 2
    job = remoteok.to_posting(entries[0], {"board": "remoteok", "company": "Remote OK"})
    assert job.is_remote is True
    assert "remoteok.com" in job.source_url.lower()
    assert job.apply_url == job.source_url


def test_remoteok_tracking_line_is_never_stored():
    from app.ingest import remoteok

    item = {"id": 1, "company": "Acme", "position": "Engineer", "url": "https://example.com/1",
            "description": "<p>Build things.</p><br/>Please mention the word **X** and tag RAAAA when applying."}
    job = remoteok.to_posting(item, {"board": "remoteok"})
    assert job.description_text == "Build things."
    assert "tag RAAAA" not in str(job.raw)
