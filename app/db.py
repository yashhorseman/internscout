"""Database connection and the migration runner.

    python -m app.db migrate
"""
import sys
from pathlib import Path

import psycopg

from app.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def connect(url: str | None = None) -> psycopg.Connection:
    # autocommit=True means nothing is left half-open by accident;
    # every multi-step change is wrapped in an explicit conn.transaction().
    return psycopg.connect(url or settings.database_url, autocommit=True)


def migrate(conn: psycopg.Connection) -> list[str]:
    """Apply every migration file not applied yet, in filename order."""
    conn.execute(
        "create table if not exists schema_migrations ("
        " filename text primary key,"
        " applied_at timestamptz not null default now())"
    )
    done = {row[0] for row in conn.execute("select filename from schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        with conn.transaction():  # the file applies completely or not at all
            conn.execute(path.read_text())
            conn.execute("insert into schema_migrations (filename) values (%s)", (path.name,))
        applied.append(path.name)
    return applied


if __name__ == "__main__":
    if sys.argv[1:] != ["migrate"]:
        sys.exit("usage: python -m app.db migrate")
    with connect() as conn:
        names = migrate(conn)
    print("applied: " + ", ".join(names) if names else "nothing to apply")
