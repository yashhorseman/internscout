"""Shapes the model must follow: tool arguments and the final answer."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field

Word = Annotated[str, Field(min_length=1, max_length=60)]


class SearchJobs(BaseModel):
    keywords: list[Word] = Field(min_length=1, max_length=6,
                                 description="Skills, role words and city names. Matched with OR.")
    query_text: str = Field(min_length=1, max_length=300,
                            description="What the user wants, as one plain sentence.")
    # the level column holds intern, entry, senior or unknown: there is no "mid"
    level: Literal["intern", "entry", "senior"] | None = None
    country_code: str | None = Field(default=None, pattern="^[A-Z]{2}$", description="For example IN.")
    is_remote: bool | None = None
    company: Word | None = None
    k: int = Field(default=8, ge=1, le=10)


class GetJob(BaseModel):
    job_id: int


class UpdateProfile(BaseModel):
    """A field that is given replaces the stored value, so send the whole list."""

    skills: list[Word] | None = Field(default=None, max_length=20)
    levels: list[Word] | None = Field(default=None, max_length=5)
    locations: list[Word] | None = Field(default=None, max_length=10)
    remote_ok: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class RecordFeedback(BaseModel):
    job_id: int
    signal: Literal["like", "dislike", "save"]


class Recommendation(BaseModel):
    job_id: int
    why: str = Field(max_length=300)
    evidence: str = Field(min_length=3, max_length=200,
                          description="A phrase copied exactly from the snippet or description, not the title.")


class AgentReply(BaseModel):
    message: str = Field(max_length=800)
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=5)
    clarifying_question: str | None = None
