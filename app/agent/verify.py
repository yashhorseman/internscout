"""Check the factual claims of a recommendation against the posting, with plain code.

The model lists what it claims (location, level, remote, skill, company). A claim is
supported only if the database says so; "not stated" counts as not supported.
"""
import re

from app.ingest.classify import COUNTRY_ALIASES

# spellings that mean the same thing
SAME = [
    {"bengaluru", "bangalore"}, {"gurugram", "gurgaon"}, {"mumbai", "bombay"},
    {"postgres", "postgresql"}, {"kubernetes", "k8s"}, {"javascript", "js"},
    {"typescript", "ts"}, {"node", "node.js", "nodejs"}, {"react", "react.js", "reactjs"},
    {"machine learning", "ml"}, {"artificial intelligence", "ai"}, {"aws", "amazon web services"},
    {"gcp", "google cloud"}, {"golang", "go"}, {"ci/cd", "continuous integration"},
]
LEVELS = {"intern": "intern", "internship": "intern", "entry": "entry", "entry level": "entry",
          "entry-level": "entry", "junior": "entry", "graduate": "entry", "new grad": "entry",
          "senior": "senior"}
REMOTE_YES = {"true", "yes", "remote", "fully remote"}
REMOTE_NO = {"false", "no", "on-site", "onsite", "in office", "in-office"}


def _spellings(value: str) -> set[str]:
    return next((group for group in SAME if value in group), {value})


def _has(phrase: str, text: str, flags=re.IGNORECASE) -> bool:
    """Whole word or phrase: "java" is not in "javascript", "C" is not in "C++"."""
    return re.search(rf"(?<![A-Za-z0-9+#]){re.escape(phrase)}(?![A-Za-z0-9+#])", text, flags) is not None


def _skill(value: str, text: str) -> bool:
    for spelling in _spellings(value):
        if spelling == "go":  # the language is written "Go"; "go" is just a verb
            if _has("Go", text, flags=0):
                return True
        elif _has(spelling, text):
            return True
    return False


def _location_part(part: str, job: dict) -> bool:
    if part == "remote":
        return job["is_remote"] is True or _has("remote", job["location"] or "")
    country = next((code for code, names in COUNTRY_ALIASES.items() if names[0] == part), None)
    if country and job["country_code"] == country:
        return True
    return any(_has(spelling, job["location"] or "") for spelling in _spellings(part))


def supported(field: str, value: str, job: dict) -> bool:
    """`job` has title, company, location, country_code, is_remote, level, description."""
    value = re.sub(r"\s+", " ", value).strip(" .").lower()
    if not value:
        return False
    if field == "company":
        return value == job["company"].lower()
    if field == "level":
        return LEVELS.get(value) == job["level"]
    if field == "remote":
        if value in REMOTE_YES:
            return job["is_remote"] is True
        if value in REMOTE_NO:
            return job["is_remote"] is False
        return value == "hybrid" and _has("hybrid", f"{job['location']} {job['description']}")
    if field == "location":
        return all(_location_part(part.strip(), job) for part in value.split(",") if part.strip())
    if field == "skill":
        return _skill(value, f"{job['title']}\n{job['description']}")
    return False


def load_job(conn, job_id: int) -> dict:
    keys = ("title", "company", "location", "country_code", "is_remote", "level", "description")
    row = conn.execute(
        "select j.title, c.name, j.location_raw, j.country_code, j.is_remote, j.level,"
        " j.description_text from jobs j join companies c on c.id = j.company_id where j.id = %s",
        (job_id,)).fetchone()
    return dict(zip(keys, row))


def failed_claims(job: dict, claims: list) -> list[str]:
    return [f"{c.field}={c.value}" for c in claims if not supported(c.field, c.value, job)]
