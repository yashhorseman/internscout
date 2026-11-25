# Where retrieval fails (development set, AI-graded)

## 1. Hybrid is worse than semantic alone
Expected the opposite. Hybrid gives the keyword list the same weight as the semantic list, and
the keyword list is much weaker here (NDCG@10 0.614 against 0.897).
Examples (NDCG@10 semantic / hybrid): "entry level jobs in data" 0.83 / 0.24; "job where I get to
break into systems and find security holes" 0.99 / 0.70; "product manager in noida" 1.00 / 0.77.
Not yet tried: a lower weight for the keyword list, or keyword search only for names.

## 2. One title can fill the whole page
"something where I can work on AI agents as a student": hybrid's top 5 are five Rubrik postings
titled "Senior AI Engineer - Enterprise Agentic ...", all graded 0 (NDCG@10 0.00). They are
separate openings, so they were kept in the index.
Two causes: "student" does not set a level filter, and nothing limits near-identical results.
Not yet tried: showing at most two results per company and title.

## 3. The re-ranker did not help
It reads the title and the first 1,000 characters of the description. In 33% of the 815
postings the company's opening "about us" text is at least that long, so the re-ranker sees
nothing about the role (52% lose at least half of the 1,000 characters).
This is a likely cause, **not yet tested**: the next experiment is to give it the text from where
the role starts (`app/retrieval/preview.py`).
Examples (hybrid / re-ranked): "frontend developer with react" 0.86 / 0.38; "security" vague
query 0.70 / 0.32.

## 4. Weak even for the best mode
"python backend role using postgres": 0.40 semantic, 0.73 re-ranked, 0.27 keyword. Not yet
diagnosed.

## 5. Queries with nothing suitable
"mechanical engineer CAD design" and "staff nurse in a hospital" have no relevant posting, yet
every mode still returns results. Search has no "nothing fits" signal; the agent has to judge.
