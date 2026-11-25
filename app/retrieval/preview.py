"""The part of a posting that is about the role, not the company's "about us" text."""
from collections import Counter, defaultdict

PREVIEW_CHARS = 1200
LONG_LINE = 60  # shorter lines are headings, never judged as repeated


def repeated_lines(postings: list[tuple[str, str]]) -> dict[str, set[str]]:
    """Per company, the long lines found in at least 10% (and at least 3) of its postings."""
    texts = defaultdict(list)
    for company, text in postings:
        texts[company].append(text)
    repeated = {}
    for company, items in texts.items():
        counts = Counter(line for text in items for line in set(text.splitlines()) if len(line) >= LONG_LINE)
        repeated[company] = {line for line, n in counts.items() if n >= max(3, 0.1 * len(items))}
    return repeated


def preview(text: str, repeated: set[str], chars: int = PREVIEW_CHARS) -> str:
    """Start at the first paragraph that is this posting's own, keeping its heading."""
    lines = [line for line in text.splitlines() if line]
    start = next((i for i, line in enumerate(lines)
                  if len(line) >= LONG_LINE and line not in repeated), 0)
    while start > 0 and len(lines[start - 1]) < LONG_LINE:
        start -= 1
    return "\n".join(lines[start:])[:chars]
