# Retrieval benchmark (2026-11-25 and 26)

**Read this first.** The queries were written by an AI assistant and the relevance grades were
assigned by an AI (a Claude subagent) under rubric version 2. A blind human check of these grades
agreed only **moderately** (weighted kappa 0.45, see below), so treat the numbers as indicative.
The held-out test queries were run **once**, on 2026-11-26, after every setting was fixed.

Setup: 815 frozen postings; 40 queries, 28 in the development set, of which 23 have at least one
relevant posting; 950 graded query-posting pairs (577 not relevant, 90 partly, 283 relevant).
Every result in every setting below was graded.

## Test set (run once)
12 held-out queries, 10 with at least one relevant posting. Settings as chosen before the run.

| Mode | Recall@5 | Recall@10 | MRR | NDCG@10 (95% interval) |
|---|---|---|---|---|
| keyword | 0.445 | 0.642 | 0.633 | 0.571 (0.342 to 0.785) |
| semantic | 0.493 | 0.759 | 0.817 | 0.803 (0.631 to 0.933) |
| hybrid | 0.584 | 0.776 | 0.950 | **0.839** (0.677 to 0.955) |
| hybrid + re-ranker | 0.482 | 0.619 | 0.917 | 0.719 (0.545 to 0.859) |

Paired differences in NDCG@10:
- hybrid over keyword: +0.269 (0.130 to 0.432)
- semantic minus hybrid: -0.036 (-0.178 to 0.093), not distinguishable
- re-ranked minus hybrid: -0.120 (-0.191 to -0.046)
- re-ranked minus semantic: -0.084 (-0.241 to 0.081), not distinguishable

What holds on both sets: hybrid clearly beats keyword search. What does **not** hold: the
development set put semantic ahead of hybrid, and the test set does not. The re-ranker did not
help on either. The default stayed hybrid, which is also the only choice that finds postings
without embeddings. Ten queries is a very small test set.

## Development set: search modes
| Mode | Recall@5 | Recall@10 | MRR | NDCG@10 (95% interval) | p50 time |
|---|---|---|---|---|---|
| keyword | 0.383 | 0.604 | 0.738 | 0.633 (0.516 to 0.743) | 1.7 ms |
| semantic | 0.491 | 0.725 | 1.000 | **0.861** (0.774 to 0.931) | 3.8 ms |
| hybrid | 0.473 | 0.686 | 0.949 | 0.811 (0.710 to 0.886) | 4.7 ms |
| hybrid + re-ranker | 0.440 | 0.636 | 0.891 | 0.789 (0.668 to 0.886) | 174 ms |

Times exclude embedding the query (about 0.4 s for a new query). Recall is low partly because
many queries have more than ten relevant postings.

Paired differences in NDCG@10:
- semantic over hybrid: +0.050 (0.008 to 0.098)
- hybrid over keyword: +0.178 (0.118 to 0.241)
- re-ranked minus hybrid: -0.022 (-0.120 to 0.071), not distinguishable
- re-ranked minus semantic: -0.071 (-0.187 to 0.025), not distinguishable

## NDCG@10 by kind of query
| Kind | Queries | keyword | semantic | hybrid | re-ranked |
|---|---|---|---|---|---|
| exact title or company | 5 | 0.844 | 1.000 | 0.960 | 1.000 |
| location | 5 | 0.511 | 0.915 | 0.815 | 0.753 |
| remote | 1 | 0.413 | 0.689 | 0.595 | 1.000 |
| seniority | 4 | 0.798 | 0.903 | 0.878 | 0.862 |
| skill | 5 | 0.494 | 0.702 | 0.682 | 0.646 |
| vague | 3 | 0.568 | 0.801 | 0.754 | 0.569 |

Groups this small show where to look, not which mode wins.

## Settings
None of these changes made a distinguishable difference in NDCG@10, so the defaults stay.

| Experiment | Change | NDCG@10 difference (95% interval) |
|---|---|---|
| E1 keyword matching | AND instead of OR, keyword mode | +0.048 (-0.039 to 0.135) |
| E1 | AND instead of OR, hybrid | +0.033 (-0.010 to 0.083) |
| E3 fusion constant | 20 instead of 60 | -0.003 (-0.018 to 0.012) |
| E3 | 100 instead of 60 | -0.004 (-0.013 to 0.001) |
| E4 re-rank depth | 20 instead of 50 | +0.009 (-0.030 to 0.051) |
| E4 | 100 instead of 50 | -0.016 (-0.037 to 0.004) |

## The agent, end to end (2026-11-26 and 27)
All 40 benchmark queries sent as plain user messages, plus 15 requests nothing in the index can
satisfy (each proven by a SQL query in `evals/no_answer.jsonl`). Full tables:
`evals/results/agent/v2/report.md` and `v3/report.md`.

Version 2 ended 14 turns without a proper answer. The logs of the **development** queries showed
two causes: the model saved a profile, searched and then opened postings one at a time until its 5
steps were gone, and it added filters such as "India" that nobody asked for. Version 3 answers
with what it has at the step limit and is told not to invent filters.

| 55 turns | Version 2 | Version 3 |
|---|---|---|
| Ended without a usable answer | 14 (25%) | 1 (2%) |
| Used all 5 tool steps | 13 (24%) | 1 (2%) |
| First answer rejected and retried | 3 (5%) | 9 (16%) |
| Seconds per turn, median | 15.8 | 9.6 |
| Tokens per turn, median | 11,493 | 10,384 |
| Scripted conversations passed | 8 of 10 | 7 of 10 |

| NDCG@10 | Plain hybrid | v2 searches | v3 searches | v2 picks | v3 picks |
|---|---|---|---|---|---|
| Development (24) | 0.770 | 0.607 | 0.767 | 0.421 | 0.441 |
| Test (10) | 0.839 | 0.598 | 0.808 | 0.507 | 0.570 |

(Plain hybrid differs from the tables above because these include the extra grades.)
**Version 3's searches are close to plain search**, which was given hand-written keywords.

The "picks" columns look poor mainly because the agent shows at most 5 jobs, often 2 or 3, while
the score counts 10 places. Compared like for like (the agent's picks against the same number of
top plain-search results), version 3's picks were relevant 85% of the time against 82% on
development (61 jobs), and 92% against 85% on test (26 jobs). That is **about the same**; these
counts are too small to call it better.

**What got worse in version 3.** It failed two conversations that version 2 passed: it did not set
the internship filter for "find me backend internships", and it asked a question instead of
searching for "I'm a fresher looking for jobs in India only". Both versions fail "I need a job"
on the check as written; version 3 does ask there, but in the message rather than the field.

## Grounding (version 3)
| | First answer | Shown to the user |
|---|---|---|
| Job ids no tool returned | 0 of 85 | none possible |
| Quote not in the posting | 7 of 85 (8%) | 0 of 82 |
| A listed claim contradicted by the database | 3 of 85 (4%) | none possible |
| AI judge finds an unsupported statement | 9 of 85 (11%) | 10 of 82 (12%) |

The code checks stop bad quotes and contradicted claims, and a retry usually repairs them (no
explanation had to be dropped). **The AI judge cannot be used as it is:** of its 10 flags on shown
explanations, several contradict the posting's own location field (for example, it marks "London"
unsupported for a job listed in London). So there is no trustworthy figure yet for statements
beyond the listed claims. That needs the human labels (`python -m evals.label_claims`) and a
better judge.

None of the 15 impossible requests produced job cards in version 3 (1 did in version 2). The
messages have not been checked by a person.

## How the grading rules were arrived at
Round one: the author re-graded 50 random pairs without seeing the AI grades. Agreement was
poor: same grade 46%, same on relevant against not relevant 64%, quadratic weighted kappa 0.36.
The author said afterwards that they had graded by their own judgment, not by the written
rubric, so this figure does not measure how well two graders apply the same rules. Looking at
the disagreements showed the rubric was loose about partial matches. The author decided three rules (another Indian city
is "partly"; if no level is asked, seniority does not matter; a different kind of work is 0), the
AI regraded all 950 pairs from scratch, and 81% of grades stayed the same.

The rules changed the conclusions, which is worth knowing:

| | round one | round two |
|---|---|---|
| semantic over hybrid, NDCG@10 | +0.100 | +0.050 |
| hybrid AND over OR | "clear" +0.035 | not distinguishable |
| re-rank depth 100 against 50 | "clear" -0.027 | not distinguishable |
| queries scored | 26 | 23 |

Round-one files: `evals/qrels_round1.jsonl`, `evals/qrels_check_round1.jsonl`.

Round two: the author blind re-graded 50 new pairs (none from round one). Same grade 68%, same on
relevant against not relevant 72%, quadratic weighted kappa 0.45. Of the 16 disagreements, 11 were
pairs the author graded 2 and the AI graded 0, so the author counted more postings as relevant.
Several of those turn on how close a neighbouring job must be to count as the same work, or go
against the written rubric as it reads. Neither set of grades was changed afterwards. The scores
above use the AI grades, and a different grader could change them, including the small lead of
semantic over hybrid. Files: `evals/qrels_check.jsonl`, `python -m evals.agreement`.

## Caveats
- An AI grader may favour what an embedding model also finds similar.
- The keyword lists in the queries were also AI-written; keyword and hybrid depend on them.
- Many comparisons with no correction for multiple testing; the semantic-over-hybrid interval
  only narrowly excludes zero.
- Relevant postings that no setting retrieved were never graded.
- In the live database 2,452 of 2,940 postings have embeddings (2026-11-27), so semantic-only
  search would never find the rest. This benchmark does not measure that.

Per-query numbers: `evals/results/`.
