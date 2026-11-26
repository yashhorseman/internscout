# InternScout

A job-search agent over a refreshed index of real job postings. **Work in progress.**

## Status
| Part | State |
|---|---|
| Ingestion from public job-board APIs, change detection, safe expiry | Done |
| Postgres schema, versioned migrations, full-text index | Done |
| Embeddings and keyword / semantic / hybrid / re-ranked search | Done |
| Retrieval benchmark | Development-set results; human check agreed moderately; test run to do |
| Chat agent (tools, memory, checked answers) and web page | First version, runs locally |
| Grounding evaluation, deployment, daily schedule | Planned |

## First benchmark results (development set)
NDCG@10 on 23 development queries over 815 real postings, **graded by an AI**: keyword 0.63,
hybrid with re-ranker 0.79, hybrid 0.81, semantic 0.86. A blind human re-grade of 50 pairs agreed
only moderately (weighted kappa 0.45).
Details and caveats: [docs/results.md](docs/results.md);
failures: [docs/failure_analysis.md](docs/failure_analysis.md).

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
    python -m evals.label --check 50         # blind human check of the grades
    python -m evals.agreement
    python -m evals.run_eval --mode hybrid --split dev

## Data sources
Public job-board APIs from Greenhouse and Lever, and the Remote OK feed.
Results from Remote OK are credited "via Remote OK" with a link to the posting.
