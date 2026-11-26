Prompt v2; 55 finished turns (40 benchmark queries and 15 with no answer).

## End to end
| Measure | Value |
|---|---|
| Turns that called search_jobs | 55/55 = 100% (93% to 100%) |
| First answer rejected (schema, id, quote or claim) | 3/55 = 5% (2% to 15%) |
| Ended without a usable answer | 14/55 = 25% (16% to 38%) |
| Seconds per turn, median / 95th percentile | 15.8 / 32.7 |
| Tokens per turn, median (input + output) | 11,493 |
| Model calls per turn, median | 5 |

## Against plain retrieval (same queries, same grades)
| Ranked list | Queries | Recall@5 | NDCG@10 | Plain hybrid Recall@5 | Plain hybrid NDCG@10 |
|---|---|---|---|---|---|
| What the agent's searches returned | 33 | 0.398 | 0.616 | 0.507 | 0.820 |
| What the agent recommended (at most 5) | 33 | 0.312 | 0.458 | 0.507 | 0.820 |

Recommended jobs with no grade (counted as not relevant): 8 of 112.

## Grounding: before (A) and after (B) the checks
| Measure | A: first answer | B: shown to the user |
|---|---|---|
| H1: ids no tool returned | 0/47 = 0% (0% to 8%) | 0 by construction |
| H2: quote not in the posting | 3/47 = 6% (2% to 17%) | 0/45 = 0% (0% to 8%) |
| H3: a listed claim fails the check | 0/47 = 0% (0% to 8%) | 0 by construction |
| H3: AI judge finds an unsupported statement | 3/47 = 6% (2% to 17%) | 2/45 = 4% (1% to 15%) |
| Explanations | 47 | 45 |
| Explanations replaced by a neutral line | | 0 |

The judge has not been compared with a person yet unless docs/results.md says so.

## H4: queries with no answer in the index
Turns that still recommended jobs: 1/15 = 7% (1% to 30%). Whether the message
admits that nothing fits has to be read by a person:

- n01 (0 cards): I could not find any software engineering internships in Japan in the current database. All available openings are in other regions such as Singapore, Ireland, the UK, Romania, and the United States. You may want to broaden your search to include other locations or check back later for new postings in Japan.
- n02 (0 cards): We currently have no postings located in Germany. The available backend developer openings returned are located in India. Below are some of those roles if you are open to exploring them.
- n03 (3 cards): I could not find any marketing jobs in Australia in our database, which currently focuses mostly on India. Here are some of our marketing openings in India in case you are open to relocating.
- n04 (0 cards): I found no job postings matching your specific COBOL and mainframe skills in our limited database. You may want to broaden your search or check other platforms.
- n05 (0 cards): I could not find any relevant veterinary doctor openings in the database. Please try widening your search or check for different roles.
- n06 (0 cards): We do not have any airline pilot jobs in our database, as our listings are primarily focused on technology, software engineering, finance, operations, and business roles from a limited set of companies in India. You may want to widen your search or check specialized aviation job boards.
- n07 (0 cards): I searched for jobs matching civil engineering and bridge construction in India, but the available postings in our database are currently only for software and technology roles. No relevant civil engineering or bridge construction positions were found.
- n08 (0 cards): I found no postings for a primary school teacher among the available companies in my search set. Please let me know if you would like to search for education-related roles or widen your search.
- n09 (0 cards): I found no relevant openings for a dentist position in our current database, as the available jobs are in tech, legal, and health insurance operations rather than clinical dentistry. You may want to widen your search by exploring healthcare-specific job portals or local dental clinic listings.
- n10 (0 cards): I could not find any job postings for a fashion designer or clothing line in our dataset. The available design roles are in software, product, instructional, and web graphic design. Please try searching for a different design field or software skills.
- n11 (0 cards): We currently do not have any openings matching aerospace propulsion engineer. You may want to widen your search by exploring general software engineering or site reliability roles.
- n12 (0 cards): Nothing relevant was found for hospital pharmacist in our database. You may want to broaden your search terms or look for general healthcare roles.
- n13 (0 cards): We could not find any openings matching your specific skills in VLSI, chip design, or Verilog in our current database. We recommend widening your search keywords to general software engineering or digital design roles.
- n14 (0 cards): We found no relevant petroleum engineering or oil rig jobs in our database, which focuses on software and technology roles. Try widening your search to software engineering, data, or site reliability roles.
- n15 (0 cards): We do not have any marine biologist research roles in our database, as our postings are primarily focused on technology and software companies in India. Therefore, no relevant jobs were found.
