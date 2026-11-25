"""Label candidates with one key press. Stop any time; it resumes where you left off.

    python -m evals.label              # grade the pool
    python -m evals.label --check 50   # grade a random 50 that already have AI grades,
                                       # without seeing them, to measure agreement

2 = clearly what the query asks for, 1 = partly, 0 = no. Rules: evals/RUBRIC.md
m = show the whole posting   u = undo   q = quit

The preview skips the paragraphs a company repeats at the start of its postings
(its "about us" text), which would otherwise fill the screen before the role does.
"""
import argparse
import json
import random
import sys
import termios
import textwrap
import tty

from app.db import connect
from app.retrieval.preview import preview, repeated_lines
from evals.common import (EARLIER_CHECKS, POOL, QRELS, QRELS_CHECK, db_url, load_grades,
                          load_queries, read_jsonl)


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


def check_sample(grades: dict[str, dict[int, int]], size: int, seed: int = 0,
                 exclude: set = frozenset()) -> list[tuple[str, int]]:
    """The same random pairs every time, so the check can be stopped and resumed."""
    pairs = sorted((q, j) for q, jobs in grades.items() for j in jobs if (q, j) not in exclude)
    return random.Random(seed).sample(pairs, min(size, len(pairs)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=int, metavar="N", help="re-grade N pairs blind")
    args = parser.parse_args()
    if not sys.stdin.isatty():
        sys.exit("run this in a terminal window")
    queries = {q["id"]: q for q in load_queries()}
    if args.check:
        seen = {(row["query_id"], row["job_id"]) for row in read_jsonl(EARLIER_CHECKS)}
        target, wanted = QRELS_CHECK, check_sample(load_grades(), args.check, exclude=seen)
    else:
        target = QRELS
        wanted = [(q, j) for q, jobs in json.loads(POOL.read_text()).items() for j in jobs]
    done = {(row["query_id"], row["job_id"]) for row in read_jsonl(target)}
    todo = [pair for pair in wanted if pair not in done]
    total, position, history, full = len(wanted), 0, [], False
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
                lines = target.read_text().splitlines()
                target.write_text("".join(line + "\n" for line in lines[:-1]))
                position = history.pop()
            elif key in ("0", "1", "2"):
                with target.open("a") as out:
                    out.write(json.dumps({"query_id": query_id, "job_id": job_id, "grade": int(key)}) + "\n")
                history.append(position)
                position += 1
    labeled = len({(row["query_id"], row["job_id"]) for row in read_jsonl(target)} & set(wanted))
    print(f"\nlabeled {labeled} of {total}")
    if args.check and labeled:
        print("see the result with: python -m evals.agreement")


if __name__ == "__main__":
    main()
