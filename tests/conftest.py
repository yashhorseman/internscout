"""Database tests use their own database (internscout_test), never the real one."""
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from app.config import settings
from app.db import connect, migrate

TEST_DB = "internscout_test"


@pytest.fixture(scope="session")
def test_db_url():
    parts = urlsplit(settings.database_url)
    admin = urlunsplit(parts._replace(path="/postgres"))
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f"drop database if exists {TEST_DB} with (force)")
        conn.execute(f"create database {TEST_DB}")
    url = urlunsplit(parts._replace(path=f"/{TEST_DB}"))
    with connect(url) as conn:
        migrate(conn)
    return url


@pytest.fixture
def db(test_db_url):
    with connect(test_db_url) as conn:
        conn.execute("truncate jobs, companies, ingest_runs, sessions restart identity cascade")
        yield conn
