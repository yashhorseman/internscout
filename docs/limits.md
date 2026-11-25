# Measured numbers and limits

Only values that were measured or read from a provider's page. Measured 2026-11-25.

## Data (local database)
| What | Value |
|---|---|
| Open postings | 2,940 from 15 boards |
| India (country_code = IN) | 748 |
| Intern or entry level (rule-based) | 97 |
| Location with no country assigned | 361 |
| Mean description length | 6,103 characters |
| Database size, no embeddings yet | 68 MB (Supabase free limit: 500 MB) |

## Models listed for our key
- Embedding: `gemini-embedding-001` (2,048 input tokens), `gemini-embedding-2`
- Chat: several Flash and Flash-Lite versions; not chosen yet

A 768-number vector from `gemini-embedding-001` is not unit length (a test call
gave 0.587), so we normalize before storing.

## Free-tier rate limits (gemini-embedding-001, from AI Studio)
- 100 requests per minute, 30,000 tokens per minute
- Daily limit: not visible on the page we read

## Embedding text
- Cut at 6,000 characters; 50 sampled postings: median 1,178 tokens, max 1,977, none over 2,048
- Priority set embedded first: 815 India, intern or entry-level postings, no failed calls and no
  daily-limit error. The other 2,125 open postings are not embedded yet.
- Database with those 815 vectors: 75 MB

## Search time (2026-11-25, M2 laptop, local database, 815 postings, 200 runs per mode)
Query vectors were already cached, so the embedding call is not included.

| Mode | p50 ms | p95 ms |
|---|---|---|
| keyword | 1.7 | 4.3 |
| semantic | 3.8 | 4.5 |
| hybrid | 4.7 | 8.0 |
| hybrid_rerank | 173.9 | 210.7 |

Embedding one query through the API: median 425 ms (only 5 calls, a rough figure).

## Chat model (2026-11-25)
`gemini-3.5-flash-lite`, set by CHAT_MODEL. Of the Flash models probed once each, it was the only
one that answered (others: 503, 504, or closed to new keys). Free-tier limits not yet recorded.
It often returns 503. First live conversation: 12 to 62 s per turn.
