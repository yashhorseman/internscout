"""Remove stored conversations.

    python -m app.admin delete-session <id>     # someone asked
    python -m app.admin purge --days 90         # retention
"""
import argparse

from app.db import connect


def delete_sessions(conn, where: str, params: tuple) -> int:
    """Messages and feedback go with the session; tool calls hold the user's words, so they go too."""
    with conn.transaction():
        conn.execute(f"delete from tool_calls where session_id in (select id from sessions where {where})",
                     params)
        return conn.execute(f"delete from sessions where {where}", params).rowcount


def delete_session(conn, session_id: str) -> int:
    return delete_sessions(conn, "id = %s", (session_id,))


def purge(conn, days: int) -> int:
    """Sessions with no message in the last `days` days."""
    return delete_sessions(
        conn, "created_at < now() - make_interval(days => %s) and not exists (select 1 from messages m"
        " where m.session_id = sessions.id and m.created_at >= now() - make_interval(days => %s))",
        (days, days))


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("delete-session").add_argument("session_id")
    commands.add_parser("purge").add_argument("--days", type=int, required=True)
    args = parser.parse_args()
    with connect() as conn:
        count = (delete_session(conn, args.session_id) if args.command == "delete-session"
                 else purge(conn, args.days))
    print(f"deleted {count} session(s)")


if __name__ == "__main__":
    main()
