# Walkthrough 3: the chat agent

## One turn, start to finish

1. `POST /sessions/{id}/messages` arrives (`app/api.py`).
2. `run_turn` (`app/agent/loop.py`) loads the last 12 messages and the saved profile.
3. **Tool loop** (at most 5 model calls): the model asks for a tool, our code runs it, the
   result goes back. The model never runs anything itself. At the limit it must answer with what
   it has.
4. **Final answer**: one more call that must return JSON matching `AgentReply`.
5. **Checks**: valid schema, every job id was returned by a tool, every evidence phrase is in
   that posting. A failure is sent back with the reason, up to 2 times.
6. **Cards** are built from database rows. The model supplies only the id, "why" and evidence.

```
user -> loop -> model: "call search_jobs(...)" -> our code -> database
                model: "call get_job(2387)"    -> our code -> database
                model: final JSON -> checks -> cards from the database -> user
```

## The pieces

| File | Job |
|---|---|
| `app/llm.py` | The only code that knows about Google. `generate()` retries overload errors |
| `app/agent/schemas.py` | Pydantic models for tool arguments and the answer |
| `app/agent/tools.py` | `search_jobs`, `get_job`, `update_profile`, `record_feedback` |
| `app/agent/prompts/v3.md` | The system prompt; earlier versions are kept |
| `app/agent/loop.py` | The loop, the checks, the fallback |
| `app/agent/store.py` | Messages, profile, call logs |
| `app/static/index.html` | The page |

## Decisions worth explaining

**The model never writes job details.** A made-up company, title or link has no path to the
screen. What it can still get wrong is the free text: `message` and `why`.

**Evidence quotes.** A cheap, exact check that the model read the posting. It does **not**
prove that `why` is true. That is the plan's next phase (claim checks and a judge).

**Memory in two layers.** The last 12 messages, plus a small profile written by the model
through a tool and put into every system prompt.

**Tool errors are data.** Bad arguments return `{"error": ...}` to the model so it can retry.

**Fallback.** If the model is busy, over quota or keeps failing the checks, the user still gets
search results, labelled "Matches your search terms".

**Likes and dislikes.** In later searches of the same session, postings near the liked ones join
the ranking as a third list, and disliked postings are left out.

## Problems found on the first real run

- The model quoted the job title as evidence and was rejected three times. The prompt and the
  error message now say the title does not count.
- Company "about us" text filled the snippet and `get_job`. Both now start at the role.
- `level="mid"` from the plan was removed: the database has no such level.
- The free model was often overloaded (503). Retries hide most of it but make turns slow:
  12 to 62 seconds in the first live conversation.

## Prompt injection

Postings are third-party text. Remote OK postings really do carry an instruction to readers
("please mention the word ...", with an encoded IP address); it is now removed on import.
Defences: tools have no effect outside the session, ids are checked, cards come from the
database. The test uses a scripted model that obeys a planted instruction and shows the app
blocks the unknown id. It does **not** show that the real model resists injection, and a
planted instruction could still bias the wording or the choice among real results.

## What the evaluation showed
Version 2 over 55 turns ended 14 without a proper answer. Reading the logs of the development
queries gave two causes: the model saved a profile, searched and then opened postings one by one
until the 5 steps were gone, and it added filters such as "India" that nobody asked for. Version 3
changes both: 1 turn in 55 now ends without an answer, and its searches score close to plain
hybrid search. It also broke two conversations that used to pass. Numbers: `docs/results.md`.

## Not done yet
- A person has not labelled explanations or checked the messages for impossible requests.
- The AI judge marks some correct statements as unsupported.
- No deployment: the server listens on this machine only.

## Questions an interviewer may ask

**Why not let the model answer from its own knowledge?** It cannot know today's openings, and
it would invent them. Every job must come from a tool.

**Why limit the loop?** A model can keep calling tools; the cap bounds cost and latency.

**Does the language model improve the search?** Not measurably. It rewrites the request into
keywords and filters, and in version 2 its guesses excluded good postings. Version 3 is close to
plain search, which had hand-written keywords. What the model adds is the conversation, the memory
and the explanations.

**Why a separate final call?** Tools and a strict output format are kept apart, so the answer
can be validated and retried without repeating searches.

**What happens if the model hallucinates a job id?** It is not in the set of ids tools
returned, so the answer is rejected; after two retries the user gets plain search results.
