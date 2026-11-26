# Where retrieval fails

Development set only, grades AI-assigned. The test queries are not examined here.

## The ten weakest queries for the shipped mode (hybrid)
Grade 2 = what was asked, 1 = partly, 0 = no. "Relevant" counts grades 1 and 2.

| NDCG@10 | Search | What went wrong | Cause |
|---|---|---|---|
| 0.14 | python backend role using postgres | The top 7 are general backend roles; eight suitable "Senior AI Engineer" postings at one company are missed | The word "backend" in a title outweighs the two named technologies, for keyword and embedding alike |
| 0.44 | job where I get to break into systems and find security holes | Defensive security roles first; the red-team postings are missed | Keywords are joined with OR, so "security" alone matches every security job |
| 0.51 | fresher customer support job | Almost everything found is only "partly" | The level rule calls "Associate" entry level; the postings ask for a year or two of experience |
| 0.60 | remote early career job | Associate roles that are not early-career | Only 15 postings are marked remote and 2 of them are relevant; nothing says "nothing else fits" |
| 0.66 | security jobs in pune | Security jobs in other cities rank with the Pune ones | There is no city filter: the city is only one keyword |
| 0.72 | java developer microservices | Half of the relevant postings are outside the top 10 | Twenty relevant postings with near-identical titles; the order among them is close to arbitrary |
| 0.74 | frontend developer with react | Full-stack and general roles between the good ones | Embeddings read these as similar. One new-grad frontend role graded 0 may be a grading error; left as is |
| 0.74 | product manager in noida | Noida roles missed while other cities appear | No city filter, as above |
| 0.82 | technical services engineer mongodb | A manager role in the top 2; "Associate TSE" missed | People management reads like the role itself; the abbreviation TSE does not match |
| 0.85 | software engineer jobs in bengaluru | Mostly correct; one manager role; recall 0.29 | 28 relevant postings cannot fit in 10 results, so this is largely the metric |

## Patterns
- **No city filter** (three queries). The cheapest likely fix: parse cities at ingestion, as is
  done for countries, and filter on them. Not done: it needs a new column and a fresh benchmark.
- **Hybrid gives the keyword list full weight.** On this development set that cost it against
  semantic search alone, but the test set did not agree, so no weight was tuned.
- **Repeated titles fill the page.** For "something where I can work on AI agents as a student"
  the top five were five openings with one senior title.
- **No "nothing fits" signal.** Every mode returns results for "staff nurse in a hospital"; the
  agent has to judge.

## Experiment: what the re-ranker reads
Hypothesis: the re-ranker did poorly because the first 1,000 characters it reads are often the
company's introduction (the whole of them in 33% of postings). Change: give it the text from where
the role starts. **The hypothesis was not supported:** NDCG@10 went from 0.751 to 0.724
(difference -0.028, 95% interval -0.114 to +0.050), still below plain hybrid at 0.770. The model
itself, trained on web search rather than job postings, may be the limit. Not adopted.
Table: `evals/results/rerank_passage.md`.

## Experiment: personalisation from one like (E6)
| | hybrid | hybrid + one like | Difference (95% interval) |
|---|---|---|---|
| Recall@10 | 0.621 | 0.666 | +0.045 (+0.007 to +0.091) |
| NDCG@10 | 0.805 | 0.848 | +0.043 (+0.003 to +0.089) |

A small gain on 22 development queries and 210 simulated likes, so the agent now uses likes and
dislikes. Read it with care: the lower end of the interval is close to zero, it was not checked on
the test set, near-identical postings at one company may account for much of it, and the weight
given to dislikes (0.5) was not tested at all.

**A lesson from this run:** before the newly surfaced postings were graded, the same experiment
showed no gain (NDCG@10 -0.015), because every ungraded posting counted as irrelevant.

These two experiments use extra grades (`evals/qrels_extra.jsonl`, 203 pairs, same AI grading
rules) for every arm, so their plain-hybrid figures differ from the benchmark tables.
