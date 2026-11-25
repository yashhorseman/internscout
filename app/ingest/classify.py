"""Small rule-based fields. Cheap, testable, and sometimes wrong on purpose:
when the rules are unsure they answer 'unknown' or None instead of guessing.
"""
import re

# Checked in this order: "Senior Associate" must be senior, not entry.
LEVEL_WORDS = {
    "intern": ["intern", "interns", "internship", "internships"],
    "senior": ["senior", "sr", "staff", "principal", "lead", "director"],
    "entry": ["graduate", "junior", "associate", "entry", "new grad"],
}

COUNTRY_ALIASES = {
    "IN": ["india", "bengaluru", "bangalore", "gurugram", "gurgaon", "mumbai", "hyderabad",
           "pune", "chennai", "noida", "new delhi", "delhi", "kolkata", "ahmedabad",
           "mohali", "lucknow"],
    "US": ["united states", "usa", "san francisco", "new york", "seattle", "chicago", "austin", "boston",
           "palo alto", "santa clara", "san mateo", "washington", "texas", "nyc"],
    "GB": ["united kingdom", "london", "england"],
    "IE": ["ireland", "dublin"],
    "DE": ["germany", "berlin", "munich"],
    "FR": ["france", "paris"],
    "CA": ["canada", "toronto", "vancouver"],
    "AU": ["australia", "sydney", "melbourne"],
    "SG": ["singapore"],
    "JP": ["japan", "tokyo"],
    "NL": ["netherlands", "amsterdam"],
    "ES": ["spain", "madrid", "barcelona"],
    "PL": ["poland", "warsaw"],
    "IL": ["israel", "tel aviv"],
    "BR": ["brazil", "são paulo", "sao paulo"],
    "MX": ["mexico", "mexico city"],
}


def _has_word(word: str, text: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) is not None


def classify_level(title: str) -> str:
    lowered = title.lower()
    for level, words in LEVEL_WORDS.items():
        if any(_has_word(word, lowered) for word in words):
            return level
    return "unknown"


def parse_country(location_raw: str | None) -> str | None:
    """Return a code only when exactly one country is mentioned."""
    if not location_raw:
        return None
    lowered = location_raw.lower()
    found = {code for code, names in COUNTRY_ALIASES.items()
             if any(_has_word(name, lowered) for name in names)}
    # "US" and "UK" only count in capitals, so the word "us" never matches
    if re.search(r"\bU\.?S\.?\b", location_raw):
        found.add("US")
    if re.search(r"\bIND\b", location_raw):
        found.add("IN")
    if re.search(r"\bUK\b", location_raw):
        found.add("GB")
    return found.pop() if len(found) == 1 else None
