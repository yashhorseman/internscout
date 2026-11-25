"""Label candidates with one key press. Stop any time; it resumes where you left off.

    python -m evals.label

2 = clearly what the query asks for, 1 = partly, 0 = no.
m = show the whole posting   u = undo   q = quit

The preview skips the paragraphs a company repeats at the start of its postings
(its "about us" text), which would otherwise fill the screen before the role does.
"""
import json
import sys
import termios
import textwrap
import tty
from collections import Counter, defaultdict

from app.db import connect
from evals.common import POOL, QRELS, db_url, load_grades, load_queries


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


def preview(text: str, repeated: set[str]) -> str:
    """Start at the first paragraph that is this posting's own, keeping its heading."""
    lines = [line for line in text.splitlines() if line]
    start = next((i for i, line in enumerate(lines)
                  if len(line) >= LONG_LINE and line not in repeated), 0)
    while start > 0 and len(lines[start - 1]) < LONG_LINE:
        start -= 1
    return "\n".join(lines[start:])[:PREVIEW_CHARS]


def wrapped(text: str) -> str:
    return "\n".join(textwrap.fill(line, 100) for line in text.splitlines())


def read_key() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main() -> None:
    if not sys.stdin.isatty():
        sys.exit("run this in a terminal window")
    queries = {q["id"]: q for q in load_queries()}
    pool = json.loads(POOL.read_text())
    done = {(q, j) for q, jobs in load_grades().items() for j in jobs}
    todo = [(q, j) for q, jobs in pool.items() for j in jobs if (q, j) not in done]
    total, position, history, full = sum(map(len, pool.values())), 0, [], False
    with connect(db_url()) as conn:
        repeated = repeated_lines(conn.execute(
            "select c.name, j.description_text from jobs j join companies c on c.id = j.company_id"
        ).fetchall())
        while position < len(todo):
            query_id, job_id = todo[position]
            query = queries[query_id]
            title, company, location, is_remote, level, text = conn.execute(
                "select j.title, c.name, j.location_raw, j.is_remote, j.level, j.description_text"
                " from jobs j join companies c on c.id = j.company_id where j.id = %s",
                (job_id,)).fetchone()
            print("\033[2J\033[H", end="")  # clear the screen
            print(f"{len(done) + position + 1} of {total}\n")
            print(f"QUERY   {query['text']}")
            print(f"FILTERS {query.get('filters') or 'none'}\n")
            remote = " | remote" if is_remote else ""
            print(f"{title}\n{company} | {location or 'location not stated'}{remote} | level: {level}\n")
            print(wrapped(text if full else preview(text, repeated.get(company, set()))))
            print("\n[2] yes   [1] partly   [0] no   [m] more/less   [u] undo   [q] quit ", end="", flush=True)
            key = read_key()
            if key == "q":
                break
            if key == "m":
                full = not full
                continue
            full = False
            if key == "u" and history:
                lines = QRELS.read_text().splitlines()
                QRELS.write_text("".join(line + "\n" for line in lines[:-1]))
                position = history.pop()
            elif key in ("0", "1", "2"):
                with QRELS.open("a") as out:
                    out.write(json.dumps({"query_id": query_id, "job_id": job_id, "grade": int(key)}) + "\n")
                history.append(position)
                position += 1
    labeled = sum(len(j) for j in load_grades().values())
    print(f"\nlabeled {labeled} of {total}")


if __name__ == "__main__":
    main()
