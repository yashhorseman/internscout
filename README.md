# InternScout

A job-search agent over a refreshed index of real job postings. **Work in progress.**

## Status
| Part | State |
|---|---|
| Ingestion from public job-board APIs, change detection, safe expiry | Done |
| Postgres schema, versioned migrations, full-text index | Done |
| Embeddings and keyword / semantic / hybrid search | Next |
| Retrieval benchmark | Planned |
| Chat agent, grounding checks, deployment, daily schedule | Planned |

## Run locally
Needs Python 3.13 and Docker (or Colima).

    python3.13 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    docker compose up -d --wait db
    python -m app.db migrate
    python -m app.ingest.run
    pytest

## Data sources
Public job-board APIs from Greenhouse and Lever, and the Remote OK feed.
Results from Remote OK are credited "via Remote OK" with a link to the posting.
