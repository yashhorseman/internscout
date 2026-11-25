"""Session memory and logs."""
from psycopg.types.json import Jsonb

HISTORY_MESSAGES = 12


def create_session(conn) -> str:
    return str(conn.execute("insert into sessions default values returning id").fetchone()[0])


def session_exists(conn, session_id: str) -> bool:
    return conn.execute("select 1 from sessions where id = %s", (session_id,)).fetchone() is not None


def load_profile(conn, session_id: str) -> dict:
    return conn.execute("select profile from sessions where id = %s", (session_id,)).fetchone()[0]


def save_profile(conn, session_id: str, changes: dict) -> dict:
    return conn.execute("update sessions set profile = profile || %s where id = %s returning profile",
                        (Jsonb(changes), session_id)).fetchone()[0]


def history(conn, session_id: str) -> list[tuple[str, dict]]:
    """The last few messages, oldest first. Older ones survive only through the profile."""
    rows = conn.execute("select role, content from messages where session_id = %s"
                        " order by id desc limit %s", (session_id, HISTORY_MESSAGES)).fetchall()
    return rows[::-1]


def seen_job_ids(conn, session_id: str) -> set[int]:
    """Every job a tool has returned in this session."""
    rows = conn.execute(
        "select distinct jsonb_array_elements_text(content->'seen_job_ids')::bigint from messages"
        " where session_id = %s and content ? 'seen_job_ids'", (session_id,))
    return {row[0] for row in rows}


def save_message(conn, session_id: str, role: str, content: dict) -> None:
    conn.execute("insert into messages (session_id, role, content) values (%s, %s, %s)",
                 (session_id, role, Jsonb(content)))


def save_feedback(conn, session_id: str, job_id: int, signal: str) -> None:
    conn.execute("insert into feedback (session_id, job_id, signal) values (%s, %s, %s)"
                 " on conflict do nothing", (session_id, job_id, signal))


def log_llm_call(conn, session_id, model, latency_ms, ok, prompt_version,
                 input_tokens=None, output_tokens=None, error=None) -> None:
    conn.execute(
        "insert into llm_calls (session_id, kind, model, input_tokens, output_tokens,"
        " latency_ms, ok, error, prompt_version) values (%s, 'chat', %s, %s, %s, %s, %s, %s, %s)",
        (session_id, model, input_tokens, output_tokens, latency_ms, ok, error, prompt_version))


def log_tool_call(conn, session_id, name, args, n_results, latency_ms, ok) -> None:
    conn.execute("insert into tool_calls (session_id, name, args, n_results, latency_ms, ok)"
                 " values (%s, %s, %s, %s, %s, %s)",
                 (session_id, name, Jsonb(args), n_results, latency_ms, ok))
