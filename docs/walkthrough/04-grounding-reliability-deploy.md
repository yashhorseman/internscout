# Walkthrough 4: grounding checks, reliability, containers

## Grounding checks (`app/agent/verify.py`)
The model must list what its explanation claims, in a fixed form:

    {"field": "skill", "value": "Python"}

Plain code checks each claim against the database row. A claim is supported only if the data says
so: `is_remote` that is *not stated* does not support "remote: true". Skills match whole words, so
"Java" is not found in "JavaScript".

An unsupported claim is sent back to the model once. If it is still there, the card stays (title,
company and link are from the database) with "Matches your search terms" instead of the
explanation.

**What this cannot catch:** the model chooses what to list. A false statement in `why` that it does
not list passes. That is why there is a second measurement, `evals/judge.py`, where another model
call reads only the posting and the explanation. The judge is itself fallible, so
`evals/label_claims.py` lets a person label the same explanations and reports how well the judge
agrees. Until that is done, judge figures are indicative only.

## Reliability
| What goes wrong | What happens | Where |
|---|---|---|
| Model overloaded or over quota | Retries, then plain search results with a notice | `llm.py`, `loop.py` |
| Our daily token budget is spent | No model call; plain search results | `loop.py` |
| Embedding the query fails | Keyword search | `tools.py`, `loop.py` |
| Database down | 503, and `/health` fails | `api.py` |
| A tool raises | The model receives `{"error": ...}` | `tools.py` |
| Too many messages | 429 after 20 in 10 minutes, per session and per address | `ratelimit.py` |
| Message over 1,000 characters | 422 | `api.py` |

Each request gets an id that appears in its JSON log line and in `llm_calls`, `tool_calls` and
`requests`. Message text is not logged. `GET /admin/stats` (bearer token) is computed by the SQL
in `app/stats.py`, including `percentile_cont` for the latency percentiles.

No CORS headers are sent, so other websites' scripts cannot read the API from a browser.

**Limits of the limits:** the rate limiter lives in memory, so it resets on restart and would not
be shared between two server processes. A new session id costs nothing, which is why the address
is limited too; an address can be shared (a college network) or changed.

## Container
`Dockerfile` builds the app without the re-ranker; `docker compose up --build` runs database and
app. `.dockerignore` is an allow list, so `.env` cannot end up in the image. The app applies
migrations on start and runs as an unprivileged user.

## Questions an interviewer may ask
**Why check claims with code instead of asking a model?** It is free, instant and repeatable, and
it fails in ways you can read. The model-based judge covers what code cannot.

**Why keep the card when the explanation fails?** The search result is still correct; only the
sentence about it is in doubt.

**Why not Redis for rate limiting?** One process and no money for another service. With two
processes it would be needed.
