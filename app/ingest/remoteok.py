"""Remote OK feed.

Its terms (returned as the first element of the response) require a followed link
back to the Remote OK URL and naming Remote OK as the source. The UI must show
"via Remote OK" with `source_url` on every such result.
"""
import re

from app.ingest.models import JobPosting
from app.ingest.text import html_to_text, repair_mojibake


# The feed ends every description with "Please mention the word X and tag Y", where Y
# is the requester's own IP address in base64. It must never be stored or published.
_TRACKING = re.compile(r"Please mention the word\b.*", re.IGNORECASE | re.DOTALL)


def without_tracking(html: str) -> str:
    return _TRACKING.sub("", html)


def url(board: dict) -> str:
    return "https://remoteok.com/api"


def items(payload) -> list[dict]:
    return [entry for entry in payload if "id" in entry]  # skips the terms notice


def to_posting(item: dict, board: dict) -> JobPosting:
    item = {**item, "description": without_tracking(item.get("description") or "")}
    return JobPosting(
        source="remoteok",
        board=board["board"],
        source_job_id=str(item["id"]),
        company=repair_mojibake(item["company"]).strip(),
        title=repair_mojibake(item["position"]).strip(),
        location_raw=repair_mojibake(item.get("location") or "") or None,
        is_remote=True,
        # the feed itself sends UTF-8 that was decoded as latin-1
        description_text=html_to_text(repair_mojibake(item["description"])),
        apply_url=item["url"],  # link to Remote OK, as their terms ask
        source_url=item["url"],
        posted_at=item.get("date"),
        raw=item,
    )
