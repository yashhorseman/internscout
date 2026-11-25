"""The one format every job source is converted into."""
from datetime import datetime

from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    source: str                      # "greenhouse" | "lever" | "remoteok"
    board: str                       # board token / site name
    source_job_id: str = Field(min_length=1)
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location_raw: str | None = None
    country_code: str | None = None  # only set here when the source states it
    is_remote: bool | None = None    # None if the source does not say
    description_text: str
    apply_url: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    posted_at: datetime | None = None
    raw: dict
