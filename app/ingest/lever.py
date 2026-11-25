"""Lever postings API. Docs: github.com/lever/postings-api"""
from datetime import datetime, timezone

from app.ingest.models import JobPosting
from app.ingest.text import clean_text, html_to_text

REMOTE_BY_WORKPLACE = {"remote": True, "onsite": False, "on-site": False, "hybrid": False}


def url(board: dict) -> str:
    host = "api.eu.lever.co" if board.get("region") == "eu" else "api.lever.co"
    return f"https://{host}/v0/postings/{board['board']}?mode=json"


def items(payload) -> list[dict]:
    return payload


def _description(item: dict) -> str:
    # The requirements live in `lists`, which descriptionPlain does not include.
    parts = [html_to_text(item.get("description"))]
    for block in item.get("lists") or []:
        parts.append(clean_text(block.get("text") or ""))
        parts.append(html_to_text(block.get("content")))
    parts.append(html_to_text(item.get("additional")))
    return "\n\n".join(p for p in parts if p)


def to_posting(item: dict, board: dict) -> JobPosting:
    categories = item.get("categories") or {}
    locations = categories.get("allLocations") or []
    location = "; ".join(locations) or categories.get("location")
    created = item.get("createdAt")
    return JobPosting(
        source="lever",
        board=board["board"],
        source_job_id=str(item["id"]),
        company=board["company"],
        title=item["text"].strip(),
        location_raw=location,
        country_code=item.get("country") or None,
        is_remote=REMOTE_BY_WORKPLACE.get(str(item.get("workplaceType")).lower()),
        description_text=_description(item),
        apply_url=item.get("applyUrl") or item["hostedUrl"],
        source_url=item["hostedUrl"],
        posted_at=datetime.fromtimestamp(created / 1000, tz=timezone.utc) if created else None,
        raw=item,
    )
