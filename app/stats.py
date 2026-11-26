"""Numbers for /admin/stats, straight from SQL. Test sessions are left out."""

# a row with no session (or a deleted one) is not known to be a test, so it counts
REAL = "not coalesce((select is_test from sessions s where s.id = t.session_id), false)"

QUERIES = {
    "requests": f"""
        select count(*) as total,
               count(*) filter (where status >= 500) as server_errors,
               count(*) filter (where status = 429) as rate_limited,
               count(*) filter (where route = 'message' and status = 200) as turns,
               percentile_cont(0.5) within group (order by latency_ms)
                 filter (where route = 'message' and status = 200) as turn_p50_ms,
               percentile_cont(0.95) within group (order by latency_ms)
                 filter (where route = 'message' and status = 200) as turn_p95_ms,
               count(*) filter (where outcome <> 'ok') as degraded_turns,
               count(*) filter (where repairs > 0) as turns_with_a_retry,
               coalesce(sum(claims_removed), 0) as explanations_removed,
               count(distinct session_id) as active_sessions
        from requests t where not is_test and created_at > now() - make_interval(hours => %(hours)s)""",
    "model_calls": f"""
        select count(*) as calls, count(*) filter (where not ok) as failed,
               coalesce(sum(input_tokens), 0) as input_tokens,
               coalesce(sum(output_tokens), 0) as output_tokens,
               percentile_cont(0.5) within group (order by latency_ms) as p50_ms,
               percentile_cont(0.95) within group (order by latency_ms) as p95_ms
        from llm_calls t where kind = 'chat' and {REAL}
          and created_at > now() - make_interval(hours => %(hours)s)""",
    "feedback": f"""
        select count(*) filter (where signal = 'like') as likes,
               count(*) filter (where signal = 'dislike') as dislikes,
               count(*) filter (where signal = 'save') as saves,
               count(*) filter (where signal = 'apply_click') as apply_clicks
        from feedback t where {REAL} and created_at > now() - make_interval(hours => %(hours)s)""",
}


def collect(conn) -> dict:
    result = {}
    for label, hours in (("last_24_hours", 24), ("last_7_days", 168)):
        result[label] = {}
        for name, sql in QUERIES.items():
            cursor = conn.execute(sql, {"hours": hours})
            columns = [c.name for c in cursor.description]
            result[label][name] = dict(zip(columns, cursor.fetchone()))
    return result
