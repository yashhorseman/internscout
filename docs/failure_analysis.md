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
company's introduction (the whole of them in 33% of postings). Change tried: give it the text
from where the role starts. Result: see `evals/results/rerank_passage.md`.

## Experiment: personalisation from one like (E6)
Result: see `evals/results/e6_personalization.md`.
