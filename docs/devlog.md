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
Next: author reviews the queries, then pooling and labeling.
