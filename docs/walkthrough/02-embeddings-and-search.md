# Walkthrough 2: embeddings, search and the benchmark

Read in this order: `app/llm.py`, `app/embed.py`, `app/retrieval/search.py`, `evals/metrics.py`.

## Embeddings
An embedding turns text into 768 numbers so that texts with similar meaning point in
similar directions. We compare directions with cosine distance (`<=>` in pgvector).

- Postings and queries use different task types (`RETRIEVAL_DOCUMENT`, `RETRIEVAL_QUERY`).
- Each vector is scaled to length 1, because 768 is not the model's native size.
- Text is cut at 6,000 characters. On 50 sampled postings the largest was 1,977 tokens
  against a limit of 2,048.
- The worker commits batch by batch, so it can be stopped and restarted.
- Free tier: 100 requests and 30,000 tokens a minute. The worker keeps its own
  60-second window so that it rarely hits the limit. A per-minute error waits and
  retries; a per-day error stops cleanly.

## The four modes
| Mode | How it ranks | Good at | Bad at |
|---|---|---|---|
| keyword | Postgres full-text, `ts_rank_cd` | exact names and skills | different words for the same thing |
| semantic | closest vectors | meaning | exact terms, company names |
| hybrid | both lists merged | usually both | costs two queries |
| hybrid_rerank | hybrid top 50, re-scored by a cross-encoder | reading query and job together | slow, large download |

**Reciprocal Rank Fusion.** A result gets `1 / (60 + rank)` from each list it appears in.
Only ranks are used, so the two lists' scores never need to be on the same scale.

**Cross-encoder.** The embedding model reads query and posting separately. A cross-encoder
reads them together, which is more accurate but too slow for every row, so it only
re-orders 50 candidates.

**OR, not AND.** "backend internship in bangalore using python" requires every word under
AND and often matches nothing. We join terms with OR and let ranking sort it out.
The benchmark will test this choice.

**Filter trap.** An approximate (HNSW) index applies filters after scanning, so it can
return too few rows. `hnsw.iterative_scan` makes it keep looking.

## The benchmark
1. Freeze a copy of the data (`evals.snapshot`), so labels stay valid.
2. For each query, pool the top 10 of all four modes (`evals.pool`).
3. Each candidate gets 0, 1 or 2 from a grader that cannot see which mode found it. Here an
   AI graded them; `evals.label --check` lets a person re-grade a sample blind.
4. Score each mode (`evals.run_eval`), tune on `dev`, report once on `test`.

- **Recall@5:** of all relevant jobs, the share in the top 5.
- **MRR:** 1 / position of the first relevant result.
- **NDCG@10:** rewards putting the best grades highest; 1.0 is a perfect order.
- **Bootstrap interval:** with 40 queries, small gaps can be luck. A mode is only called
  better if the interval for the difference excludes zero.

## Limitations to state openly
- Queries were drafted by an AI assistant; the author reviewed them and made no changes.
- Company "about us" text is long and repeated across postings, and it is embedded and keyword-indexed with the rest. Its effect on ranking is not yet measured.
- 40 queries; one AI grader, single pass. A first human check agreed poorly (kappa 0.36), so the
  rubric was tightened and everything regraded; a second check on the new grades agreed moderately (kappa 0.45). The one test run did not
  confirm that semantic beats hybrid.
- A relevant job that no mode retrieved is unlabeled and counts as not relevant.
- The corpus is India-based plus intern and entry-level postings, not the whole index.
- Queries with no relevant job are left out of every average, including MRR.

Results: docs/results.md. What went wrong: docs/failure_analysis.md.

## Interview questions
1. *Why not just add the two scores?* They are on unrelated scales.
2. *Why a separate test split?* Settings tuned on a set always look good on that set.
3. *Why pool?* Labeling every job for every query is too much work.
4. *Why does recall depend on the pool?* Its denominator is only the jobs found and labeled.
