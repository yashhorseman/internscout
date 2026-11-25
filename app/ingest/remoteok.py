"""Remote OK feed.

Its terms (returned as the first element of the response) require a followed link
back to the Remote OK URL and naming Remote OK as the source. The UI must show
"via Remote OK" with `source_url` on every such result.
"""
from app.ingest.models import JobPosting
from app.ingest.text import html_to_text


def url(board: dict) -> str:
    return "https://remoteok.com/api"


def items(payload) -> list[dict]:
    return [entry for entry in payload if "id" in entry]  # skips the terms notice


def to_posting(item: dict, board: dict) -> JobPosting:
    return JobPosting(
        source="remoteok",
        board=board["board"],
        source_job_id=str(item["id"]),
        company=item["company"].strip(),
        title=item["position"].strip(),
        location_raw=item.get("location") or None,
        is_remote=True,
        description_text=html_to_text(item.get("description")),
        apply_url=item["url"],  # link to Remote OK, as their terms ask
        source_url=item["url"],
        posted_at=item.get("date"),
        raw=item,
    )
