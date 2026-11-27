Prompt v3; 55 finished turns (40 benchmark queries and 15 with no answer).

## End to end
| Measure | Value |
|---|---|
| Turns that used all 5 tool steps | 1/55 = 2% (0% to 10%) |
| Turns that called search_jobs | 55/55 = 100% (93% to 100%) |
| First answer rejected (schema, id, quote or claim) | 9/55 = 16% (9% to 28%) |
| Ended without a usable answer | 1/55 = 2% (0% to 10%) |
| Seconds per turn, median / 95th percentile | 9.6 / 27.9 |
| Tokens per turn, median (input + output) | 10,384 |
| Model calls per turn, median | 4 |

## Against plain retrieval (same queries, same grades)
| Ranked list | Split | Queries | Recall@5 | NDCG@10 | Plain hybrid Recall@5 | Plain hybrid NDCG@10 |
|---|---|---|---|---|---|---|
| What the agent's searches returned | dev | 24 | 0.417 | 0.767 | 0.421 | 0.770 |
| What the agent's searches returned | test | 10 | 0.561 | 0.808 | 0.579 | 0.839 |
| What the agent recommended (at most 5) | dev | 24 | 0.275 | 0.441 | 0.421 | 0.770 |
| What the agent recommended (at most 5) | test | 10 | 0.422 | 0.570 | 0.579 | 0.839 |

## Like for like: the agent's picks against the same number of plain-search results
NDCG@10 penalises a short list, so this counts how many of the shown jobs are relevant.
A query counts only when the agent recommended something.

| Split | Queries | Jobs shown | Agent: relevant / grade 2 | Plain hybrid: relevant / grade 2 |
|---|---|---|---|---|
| dev | 26 | 61 | 85% / 79% | 82% / 75% |
| test | 11 | 26 | 92% / 88% | 85% / 81% |

Recommended jobs with no grade (counted as not relevant): 0 of 87.

## Grounding: before (A) and after (B) the checks
| Measure | A: first answer | B: shown to the user |
|---|---|---|
| H1: ids no tool returned | 0/85 = 0% (0% to 4%) | 0 by construction |
| H2: quote not in the posting | 7/85 = 8% (4% to 16%) | 0/82 = 0% (0% to 4%) |
| H3: a listed claim fails the check | 3/85 = 4% (1% to 10%) | 0 by construction |
| H3: AI judge finds an unsupported statement | 9/85 = 11% (6% to 19%) | 10/82 = 12% (7% to 21%) |
| Explanations | 85 | 82 |
| Explanations replaced by a neutral line | | 0 |

The judge has not been compared with a person yet unless docs/results.md says so.

## H4: queries with no answer in the index
Turns that still recommended jobs: 0/15 = 0% (0% to 20%). Whether the message
admits that nothing fits has to be read by a person:

- n01 (0 cards): No software engineering internship or role was found in Japan in the current database. Please consider widening your search to other locations or check back later.
- n02 (0 cards): I could not find any backend developer jobs in Germany in the current postings, as the available roles are primarily located in India. You may want to broaden your location preferences or check back later when more international postings are added.
- n03 (0 cards): I found no marketing jobs located in Australia in our current database, as our listings are primarily focused on India. Here are some marketing roles available in other regions if you would like to consider them.
- n04 (0 cards): No relevant COBOL or mainframe jobs were found in the current listings. Please widen your search to other related technologies or backend software engineering roles.
- n05 (0 cards): We found no relevant job postings for veterinary doctors in our database. You may want to broaden your search or check specialized veterinary job boards.
- n06 (0 cards): We found no airline pilot jobs in our database, as our listings are primarily focused on technology, finance, and operations roles in India. Please consider searching for roles in aviation or travel operations if available, or broaden your search.
- n07 (0 cards): I found no matching civil engineering or bridge construction jobs in the system. The current listings are primarily software engineering, infrastructure, and financial technology roles. Please let me know if you would like to search for software or other roles instead.
- n08 (0 cards): I searched for primary school teacher roles, but the available job listings do not currently include teaching positions. Here are some of the other open roles available in our database.
- n09 (0 cards): I found no postings for a dentist position at a clinic in our current job database, which focuses mostly on technology, legal, finance, and corporate roles. You may want to check specialized healthcare job boards or local clinic websites directly.
- n10 (0 cards): I searched for fashion designer roles, but the available postings from our partner companies are focused on software, product, and graphic design rather than apparel or clothing design. Here is a clarifying question to help direct your search.
- n11 (0 cards): I found no aerospace propulsion engineer roles in the current database. You may want to widen your search by looking for general engineering or software roles.
- n12 (0 cards): We couldn't find any job postings related to hospital pharmacist in our database. You might want to try broadening your search or checking specialized healthcare job boards.
- n13 (0 cards): I found no job postings matching your specific skills in VLSI chip design with Verilog among the available search results. The current database contains design roles related to software and UI/UX product design rather than hardware or semiconductor design. Please let me know if you would like to explore software design roles or other available technical domains.
- n14 (0 cards): We do not have any listings for petroleum engineers or oil rig operations. Our current openings are primarily software, data, and infrastructure engineering roles in technology companies.
- n15 (0 cards): I searched our available job postings for marine biology or marine research roles, but none were found among our current tech and corporate listings in India. We suggest widening your search to specialized environmental or marine science platforms.
