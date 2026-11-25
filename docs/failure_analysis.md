# Where retrieval fails (development set, AI-graded, provisional)

## 1. Hybrid does not beat semantic alone
Expected the opposite. Hybrid gives the keyword list the same weight as the semantic list, and
the keyword list is much weaker here (NDCG@10 0.633 against 0.861).
Examples (NDCG@10 semantic / hybrid): "job where I get to break into systems and find security
holes" 0.78 / 0.44; "product manager in noida" 1.00 / 0.74; "sql data analysis and dashboards"
1.00 / 0.89.
Not yet tried: a lower weight for the keyword list, or keyword search only for names.

## 2. One title can fill the whole page
"something where I can work on AI agents as a student": hybrid's top 5 are five Rubrik postings
titled "Senior AI Engineer - Enterprise Agentic ...", none suitable for a student. They are
separate openings, so they were kept in the index.
Two causes: "student" does not set a level filter, and nothing limits near-identical results.
Not yet tried: showing at most two results per company and title.

## 3. The re-ranker did not help, at about 40 times the search time
It reads the title and the first 1,000 characters of the description. In 33% of the 815
postings the company's opening "about us" text is at least that long, so the re-ranker sees
nothing about the role (52% lose at least half of the 1,000 characters).
This is a likely cause, **not yet tested**: the next experiment is to give it the text from where
the role starts (`app/retrieval/preview.py`).
Examples (hybrid / re-ranked): "frontend developer with react" 0.74 / 0.25; the security-holes
query 0.44 / 0.00. It does help some: "python backend role using postgres" 0.14 / 0.73.

## 4. Weak even for the best mode
"python backend role using postgres": 0.22 semantic, 0.06 keyword. Only the re-ranker does
well (0.73). Not yet diagnosed.

## 5. Queries with nothing suitable
Five development queries have no relevant posting (for example "staff nurse in a hospital" and
"mechanical engineer CAD design"), yet every mode still returns results. Search has no "nothing
fits" signal; the agent has to judge.
