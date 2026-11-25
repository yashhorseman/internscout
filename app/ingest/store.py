"""Write one board's fetch into the database: new, changed, unchanged, gone."""
import logging
from datetime import datetime, timedelta

import psycopg
from psycopg.types.json import Jsonb

from app.ingest.classify import classify_level, parse_country
from app.ingest.models import JobPosting
from app.ingest.text import content_hash

log = logging.getLogger("ingest")


def _company_id(conn: psycopg.Connection, name: str) -> int:
    row = conn.execute("select id from companies where name = %s", (name,)).fetchone()
    if row is None:
        row = conn.execute("insert into companies (name) values (%s) returning id", (name,)).fetchone()
    return row[0]


def upsert(conn: psycopg.Connection, job: JobPosting, seen_at: datetime) -> str:
    """Insert or update one posting. Returns 'new', 'changed' or 'unchanged'."""
    digest = content_hash(job.title, job.location_raw, job.description_text)
    company_id = _company_id(conn, job.company)
    country = job.country_code or parse_country(job.location_raw)
    level = classify_level(job.title)
    old = conn.execute(
        "select content_hash, status, board, company_id, country_code, level, is_remote,"
        " apply_url, source_url, posted_at from jobs where source = %s and source_job_id = %s",
        (job.source, job.source_job_id),
    ).fetchone()
    outcome = "new" if old is None else "changed" if old[0] != digest else "unchanged"
    current = (digest, "open", job.board, company_id, country, level, job.is_remote,
               job.apply_url, job.source_url, job.posted_at)
    if old == current:
        # Nothing to rewrite. Touching only last_seen_at keeps the table from bloating.
        conn.execute(
            "update jobs set last_seen_at = %s where source = %s and source_job_id = %s",
            (seen_at, job.source, job.source_job_id),
        )
        return outcome
    values = {
        "source": job.source, "board": job.board, "sid": job.source_job_id,
        "company_id": company_id, "title": job.title,
        "location": job.location_raw,
        "country": country,
        "remote": job.is_remote, "level": level,
        "description": job.description_text, "apply_url": job.apply_url,
        "source_url": job.source_url, "posted_at": job.posted_at, "hash": digest,
        "raw": Jsonb(job.raw), "seen_at": seen_at,
    }
    # One statement covers all three cases. A closed job that reappears is reopened.
    # embedding_stale only turns on when the text that gets embedded has changed.
    conn.execute(
        """
        insert into jobs (source, board, source_job_id, company_id, title, location_raw,
                          country_code, is_remote, level, description_text, apply_url,
                          source_url, posted_at, content_hash, raw, first_seen_at, last_seen_at)
        values (%(source)s, %(board)s, %(sid)s, %(company_id)s, %(title)s, %(location)s,
                %(country)s, %(remote)s, %(level)s, %(description)s, %(apply_url)s,
                %(source_url)s, %(posted_at)s, %(hash)s, %(raw)s, %(seen_at)s, %(seen_at)s)
        on conflict (source, source_job_id) do update set
          board = excluded.board, company_id = excluded.company_id, title = excluded.title,
          location_raw = excluded.location_raw, country_code = excluded.country_code,
          is_remote = excluded.is_remote, level = excluded.level,
          description_text = excluded.description_text, apply_url = excluded.apply_url,
          source_url = excluded.source_url, posted_at = excluded.posted_at,
          raw = excluded.raw, last_seen_at = excluded.last_seen_at,
          status = 'open', closed_at = null,
          embedding_stale = jobs.embedding_stale or jobs.content_hash <> excluded.content_hash
            or jobs.level <> excluded.level or jobs.company_id <> excluded.company_id,
          content_hash = excluded.content_hash
        """,
        values,
    )
    return outcome


def close_missing(conn: psycopg.Connection, source: str, board: str, run_started: datetime,
                  fetched: int, expire_after_days: int | None = None) -> int:
    """Close postings that disappeared. Call only after a successful fetch.

    expire_after_days is for feeds that list only the latest jobs: there,
    missing from the feed does not mean gone, so wait that long first.
    """
    if fetched == 0:
        open_now = conn.execute(
            "select count(*) from jobs where source = %s and board = %s and status = 'open'",
            (source, board),
        ).fetchone()[0]
        if open_now:
            log.warning("%s/%s returned 0 jobs but %d are open: closing nothing",
                        source, board, open_now)
        return 0
    cutoff = run_started - timedelta(days=expire_after_days or 0)
    cursor = conn.execute(
        "update jobs set status = 'closed', closed_at = %s "
        "where source = %s and board = %s and status = 'open' and last_seen_at < %s",
        (run_started, source, board, cutoff),
    )
    return cursor.rowcount
