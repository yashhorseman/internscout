# Deploying (not done yet)

Everything below needs an account action or publishes something, so it waits for the author.
Provider screens and limits change: check each page when you get there.

## 0. Run the whole system on a laptop
    docker compose up --build        # http://127.0.0.1:8000

## 1. GitHub (private repository)
- Create a private repository, then `git remote add origin <url>` and `git push -u origin main`.
- Check first: `git log --format='%an <%ae>' | sort -u` shows the name and email on every commit.
- CI (`.github/workflows/ci.yml`) runs on that push. A private repository uses the account's
  included Actions minutes; check the allowance and set the spending limit so nothing is billed.

## 2. Database (Supabase free project)
- Create the project, run `create extension if not exists vector;`.
- Copy a connection string from the "Connect" page. With a transaction-mode pooler, read
  psycopg's notes on prepared statements first.
- From the laptop, with `DATABASE_URL` set to it:
  `python -m app.db migrate && python -m app.ingest.run && python -m app.embed`
- Check the size: `select pg_size_pretty(pg_database_size(current_database()));` (free limit 500 MB).

## 3. Daily refresh
Add `DATABASE_URL` and `GEMINI_API_KEY` as repository secrets. Run the "daily refresh" workflow
once by hand and read its log. Until both secrets exist it does nothing.

## 4. Web service (Render free)
- New Web Service from the repository, Docker runtime.
- Environment: `DATABASE_URL`, `GEMINI_API_KEY`, `ADMIN_TOKEN` (long random string).
- Health check path `/health`.
- Then: `python scripts/smoke.py https://<your-service-address>`

## Before sharing the link
- The rate limit counts by the caller's address. Behind a host's proxy that may be the proxy's
  address, making everyone share one limit: check the request logs, and if so, start uvicorn with
  `--proxy-headers --forwarded-allow-ips` set as the host documents.
- The free service sleeps when idle, so the first visit is slow. Say so when you share it.
