# Walkthrough 1: data and database

## The flow
`sources.yaml` lists boards. For each one, `app/ingest/run.py`:
1. fetches its JSON (`fetch.py`),
2. converts every item into one `JobPosting` shape (`greenhouse.py`, `lever.py`, `remoteok.py`),
3. writes it (`store.py`): new, changed, unchanged or closed,
4. records one row in `ingest_runs`.

Read the files in that order.

## Ideas to understand

**One internal format.** Each source names things differently. Converting at the edge
means nothing else in the code knows which source a job came from. Pydantic rejects
a posting with a missing title or link at that edge.

**Idempotent ingestion.** Running it twice gives the same result. Two things make that
true: `unique (source, source_job_id)` makes duplicates impossible, and
`insert ... on conflict do update` handles insert and update in one statement.

**Change detection.** We store a SHA-256 hash of title, location and description.
A different hash means the text changed, so the posting must be embedded again
(`embedding_stale = true`). Embedding is the scarce resource on a free tier.

**Safe closing.** A posting not seen in a successful fetch is closed, not deleted.
Nothing is closed if the board errored, returned zero jobs, or had an item we could
not read. Otherwise one outage would empty the index.

**One transaction per board.** All of a board's writes succeed or none do, and one
broken board does not stop the others.

**Migrations.** Each schema change is a numbered SQL file applied once and recorded in
`schema_migrations`. An applied file is never edited; `003_fillfactor.sql` is an example
of changing a table afterwards.

**Constraints.** `check` rules make the database refuse bad values even if the code is wrong.

**Full-text search.** `fts` is a generated column, so it cannot drift from the text.
Titles get weight A, descriptions B, locations C. A GIN index maps each word to the
rows containing it.

**SQL injection.** Values are always passed as `%s` or `%(name)s` parameters.

## Where we differ from the original plan, and why
| Change | Reason |
|---|---|
| `jobs.board` and `ingest_runs.board` added | Closing works per board; company name is not a reliable stand-in |
| `jobs.raw` column added | The plan's model had it, its table did not |
| "Internship" counts as intern | Matching only the whole word "intern" missed it |
| Senior is checked before entry | "Senior Associate" is not entry level |
| Remote OK closes only after 30 days unseen | Its feed shows only the latest ~100 jobs. 30 is a choice, not a measured value |
| Unchanged rows only update `last_seen_at` | Rewriting them grew the database from 63 MB to 115 MB |
| `vacuum analyze` after ingestion | Without it the planner skipped the full-text index |

## Known weaknesses
- Level rules leave most titles `unknown`; there is no `mid` rule.
- 361 postings have no country, so a country filter will not find them.
- A location naming two countries gets none.

## Questions an interviewer might ask
Try answering before reading the answer.

1. *Why hash instead of comparing "updated at"?* Not every source provides it, and a
   timestamp can change when the text does not.
2. *What if the API returns an empty list by mistake?* The guard in `close_missing`
   closes nothing and logs a warning.
3. *Why keep closed rows?* Debugging, and evaluation labels still refer to them.
4. *Why did your index stop being used?* Two causes at different times: stale statistics
   after a bulk load, then unmerged entries in the GIN index after many updates.
   `explain analyze` showed it, and `vacuum analyze` fixed it.
5. *Why Postgres and not a separate vector database?* One service holds text, keyword
   index, vectors and logs, so there is nothing to keep in sync.

## Try it yourself
    colima start && docker compose up -d --wait db
    docker compose exec db psql -U postgres -d internscout
Then run the queries in `docs/practice_queries.sql`.
