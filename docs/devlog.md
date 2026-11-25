# Devlog

## 2026-11-25
Worked: schema and migrations; ingestion from 15 boards; 19 tests; Gemini key verified.
Broke and fixed:
- Re-running ingestion rewrote every row (63 MB grew to 115 MB). Unchanged rows now only get last_seen_at.
- Keyword search ignored the full-text index after bulk writes. Ingestion now runs `vacuum analyze`.
- Locations such as "Mohali, IND" had no country.
Later: embedding worker, four search modes, benchmark tools and 40 draft queries; 45 tests.
Evening: embedded 815 postings, froze the evaluation snapshot, measured latency.
Seen: many same-title postings are separate openings with different text; kept all.
Night: queries approved unchanged; pooled 776 query-posting pairs (420 different postings).
Broke and fixed:
- The labeling screen showed the first 500 characters, which for most companies was "about us" text.
- Remote OK sends garbled punctuation (UTF-8 read as latin-1). Repaired on import; the frozen corpus
  still has 3 affected postings.
Then: author chose AI grading; a Claude subagent graded the pool. First chat agent and page built.
- Remote OK appends a line holding the requester's IP in base64; it had reached a committed test file.
- The agent quoted job titles as evidence until the prompt said not to.
- Benchmark on dev: semantic beat hybrid and the re-ranker, against expectation. See failure_analysis.md.
- Human check of 50 grades: weighted kappa 0.36. Test run held until the grading rules are tightened.
