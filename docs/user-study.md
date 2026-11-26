# User study (after deployment; not started)

## Before inviting anyone
- Set `MARK_SESSIONS_AS_TEST=true` wherever you test, so your own sessions are left out.
- The page already says what is stored and for how long (90 days, applied by the daily workflow's
  `app.admin purge`). Change both together if you choose another period.
- Deletion on request: `python -m app.admin delete-session <id>`.

## Who
At least 10 people other than you who are looking for internships. No incentives, no bulk
messages to strangers.

## Message
> I built a small tool that searches internship and early-career postings and explains why each
> might fit. Could you try to find one you would actually apply to, then answer three questions?
> <link>  (the first load can take a minute)

## The three questions
1. Did you find at least one job you would consider applying to? (Yes / No / Not sure)
2. What was missing or wrong?
3. How good were the explanations next to each job? (1 to 5)

## What to report
From `GET /admin/stats` (take a dated copy at the start and end) and the form: sessions, searches,
likes, dislikes, saves, apply clicks, share of degraded answers, median and 95th-percentile time,
and every form count. Report only what can be reproduced from the database or the form export.
A small number is fine if it is true.
