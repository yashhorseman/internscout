"""Label candidates with one key press. Stop any time; it resumes where you left off.

    python -m evals.label

2 = clearly what the query asks for, 1 = partly, 0 = no.   u = undo   q = quit
"""
import json
import sys
import termios
import textwrap
import tty

from app.db import connect
from evals.common import POOL, QRELS, db_url, load_grades, load_queries


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
    total, position, history = sum(map(len, pool.values())), 0, []
    with connect(db_url()) as conn:
        while position < len(todo):
            query_id, job_id = todo[position]
            query = queries[query_id]
            title, company, location, level, text = conn.execute(
                "select j.title, c.name, j.location_raw, j.level, left(j.description_text, 500)"
                " from jobs j join companies c on c.id = j.company_id where j.id = %s",
                (job_id,)).fetchone()
            print("\033[2J\033[H", end="")  # clear the screen
            print(f"{len(done) + position + 1} of {total}\n")
            print(f"QUERY   {query['text']}")
            print(f"FILTERS {query.get('filters') or 'none'}\n")
            print(f"{title}\n{company} | {location or 'location not stated'} | {level}\n")
            for line in text.splitlines():
                print(textwrap.fill(line, 100))
            print("\n[2] yes   [1] partly   [0] no   [u] undo   [q] quit ", end="", flush=True)
            key = read_key()
            if key == "q":
                break
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
