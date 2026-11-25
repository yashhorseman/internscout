# InternScout

A job-search agent over a refreshed index of real job postings. **Work in progress.**

## Status
| Part | State |
|---|---|
| Ingestion from public job-board APIs, change detection, safe expiry | Done |
| Postgres schema, versioned migrations, full-text index | Done |
| Embeddings and keyword / semantic / hybrid / re-ranked search | Done |
| Retrieval benchmark | AI-graded; results being produced |
| Chat agent (tools, memory, checked answers) and web page | First version, runs locally |
| Grounding evaluation, deployment, daily schedule | Planned |

## Run locally
Needs Python 3.13 and Docker (or Colima).

    python3.13 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    docker compose up -d --wait db
    python -m app.db migrate
    python -m app.ingest.run
    pytest

## Search
    python -m app.embed --priority-only
    python -m app.retrieval.cli "python backend internship" --mode hybrid --level intern

## Chat agent
    uvicorn app.api:app          # then open http://127.0.0.1:8000

How it works: docs/walkthrough/03-agent.md.

## Retrieval benchmark
    pip install -r requirements-rerank.txt
    python -m evals.snapshot
    python -m evals.pool
    python -m evals.label                    # grading rules: evals/RUBRIC.md
    python -m evals.run_eval --mode hybrid --split dev

## Data sources
Public job-board APIs from Greenhouse and Lever, and the Remote OK feed.
Results from Remote OK are credited "via Remote OK" with a link to the posting.
