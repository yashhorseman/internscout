"""Greenhouse job board API. Docs: developers.greenhouse.io/job-board"""
import html

from app.ingest.models import JobPosting
from app.ingest.text import html_to_text


def url(board: dict) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{board['board']}/jobs?content=true"


def items(payload) -> list[dict]:
    return payload["jobs"]


def to_posting(item: dict, board: dict) -> JobPosting:
    location = (item.get("location") or {}).get("name")
    return JobPosting(
        source="greenhouse",
        board=board["board"],
        source_job_id=str(item["id"]),
        company=board["company"],
        title=item["title"].strip(),
        location_raw=location,
        # Greenhouse has no remote field; only the location text can say so
        is_remote=True if location and "remote" in location.lower() else None,
        # the HTML arrives escaped (&lt;div&gt;), so unescape before parsing
        description_text=html_to_text(html.unescape(item.get("content") or "")),
        apply_url=item["absolute_url"],
        source_url=item["absolute_url"],
        posted_at=item.get("first_published"),
        raw=item,
    )
