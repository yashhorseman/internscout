# Labeling rubric (version 2)

Grade each posting against the search **and its filters**, from what the posting says.
Used by the AI grader (qrels.jsonl) and by the person checking it.

## First question: is it the right kind of work?
Right kind of work means the day-to-day job is what the search asks for. A matching company,
city or keyword does not count on its own. **Different kind of work: 0**, even at the company
named. A neighbouring job whose main tasks differ is different work. So is people management
when the search asks for hands-on work.

## If it is the right kind of work
| Grade | When |
|---|---|
| 2 | Everything the search states is met |
| 1 | One stated thing is only partly met (list below) |
| 0 | Something stated is clearly not met |

**1 (partly):**
- The search names a city and the job is in **another Indian city**.
- The search says remote and the job is hybrid.
- The search names several skills and only some are part of the job. A skill listed only as
  nice to have is not part of the job.
- The search is for entry-level work and the job asks for a little experience (about 1 to 2 years).

**0:**
- A senior, staff, lead or manager role for an intern or entry-level search.
- A different company from the one named.
- A city search and a job outside India.
- A remote search and an on-site job.
- Two of the "partly" cases at once.

## When the search names no level
Seniority does not matter: a senior, staff, lead or architect role doing that work is a **2**.

## Other rules
- A job open in several places counts for a city if that city is one of them.
- If you cannot tell from the posting, give the lower grade.
- Some searches have nothing suitable. Do not be generous to fill them.
