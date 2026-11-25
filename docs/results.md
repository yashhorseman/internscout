# Retrieval benchmark: development-set results (2026-11-25)

**Read the caveats first.** The queries were written by an AI assistant and the relevance
grades were assigned by an AI (a Claude subagent). A blind human re-grade of 50 pairs agreed
poorly with it (below). The 12 held-out test queries have not been run.

Setup: 815 frozen postings; 40 queries, 28 in the development set, of which 26 have at least one
relevant posting; 950 graded query-posting pairs (429 not relevant, 257 partly, 264 relevant).
Every result in every setting below was graded.

## Human check of the grades
The author re-graded 50 random pairs without seeing the AI grades.

| Measure | Value |
|---|---|
| Same grade | 46% |
| Same on relevant (1 or 2) against not (0) | 64% |
| Quadratic weighted kappa | 0.36 (low) |

Much of the gap is the middle grade: the AI gave "partly" 21 times, the author 6. Six pairs got
opposite verdicts (0 against 2).

Does the mode order depend on how "partly" is read? Using the AI grades, NDCG@10:

| "Partly" counts as | keyword | semantic | hybrid | re-ranked | semantic minus hybrid |
|---|---|---|---|---|---|
| partly (as graded) | 0.614 | 0.897 | 0.797 | 0.764 | +0.100 (0.037 to 0.173) |
| not relevant (23 queries) | 0.553 | 0.842 | 0.779 | 0.771 | +0.063 (0.002 to 0.127) |
| fully relevant | 0.774 | 0.965 | 0.885 | 0.826 | +0.080 (0.020 to 0.152) |

The order holds. This does not cover disagreements about relevant against not relevant.

## Search modes
| Mode | Recall@5 | Recall@10 | MRR | NDCG@10 (95% interval) | p50 time |
|---|---|---|---|---|---|
| keyword | 0.330 | 0.530 | 0.894 | 0.614 (0.515 to 0.713) | 1.7 ms |
| semantic | 0.397 | 0.680 | 1.000 | **0.897** (0.837 to 0.946) | 3.8 ms |
| hybrid | 0.378 | 0.611 | 0.931 | 0.797 (0.697 to 0.886) | 4.7 ms |
| hybrid + re-ranker | 0.351 | 0.570 | 0.870 | 0.764 (0.656 to 0.864) | 174 ms |

Times exclude embedding the query (about 0.4 s for a new query). Recall is low partly because
many queries have more than ten relevant postings.

Paired differences in NDCG@10:
- semantic over hybrid: +0.100 (0.037 to 0.173)
- hybrid over keyword: +0.183 (0.121 to 0.241)
- re-ranked minus hybrid: -0.033 (-0.101 to 0.039), not distinguishable

## NDCG@10 by kind of query
| Kind | Queries | keyword | semantic | hybrid | re-ranked |
|---|---|---|---|---|---|
| exact title or company | 5 | 0.846 | 0.990 | 0.957 | 0.990 |
| skill | 5 | 0.561 | 0.790 | 0.746 | 0.665 |
| seniority | 5 | 0.580 | 0.913 | 0.743 | 0.705 |
| location | 5 | 0.534 | 0.931 | 0.817 | 0.762 |
| remote | 2 | 0.551 | 0.941 | 0.914 | 0.990 |
| vague | 4 | 0.563 | 0.829 | 0.643 | 0.567 |

Groups this small show where to look, not which mode wins.

## Settings
| Experiment | Change | NDCG@10 difference (95% interval) |
|---|---|---|
| E1 keyword matching | AND instead of OR, keyword mode | +0.023 (-0.052 to 0.104); Recall@10 fell by 0.078 |
| E1 | AND instead of OR, hybrid | +0.035 (0.004 to 0.068) |
| E3 fusion constant | 20 instead of 60 | -0.004 (-0.013 to 0.004) |
| E3 | 100 instead of 60 | -0.002 (-0.007 to 0.000) |
| E4 re-rank depth | 20 instead of 50 | +0.031 (-0.016 to 0.076) |
| E4 | 100 instead of 50 | -0.027 (-0.047 to -0.009) |

## Caveats
- An AI grader may favour what an embedding model also finds similar. In the 50 checked pairs the
  AI was more generous than the author for keyword results (75% relevant against 62%) as well as
  semantic ones (71% against 62%); too few pairs to rule a bias out.
- The keyword lists in the queries were also AI-written; keyword and hybrid depend on them.
- Eleven comparisons with no correction for multiple testing: small "clear" differences such
  as hybrid AND vs OR may be chance.
- Relevant postings that no setting retrieved were never graded.
- In the live database only 815 of 2,940 postings have embeddings, so semantic-only search
  would never find the rest. This benchmark does not measure that.

Per-query numbers: `evals/results/`.
