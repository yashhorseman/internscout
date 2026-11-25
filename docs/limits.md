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

## Free-tier rate limits
Not recorded yet. Read them from aistudio.google.com/rate-limit.
