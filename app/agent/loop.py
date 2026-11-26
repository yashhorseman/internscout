"""One conversation turn: let the model use tools, then check its answer before showing it."""
import json
import logging
import re
import time
from pathlib import Path

from pydantic import ValidationError

from app import llm
from app.agent import store, tools, verify
from app.agent.schemas import AgentReply
from app.config import settings
from app.retrieval.search import search

log = logging.getLogger(__name__)

MAX_STEPS = 5       # model calls that may use tools, per turn
MAX_REPAIRS = 2     # extra attempts when the final answer fails the checks
PROMPT_VERSION = "v3"
PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.md").read_text()
NEUTRAL_WHY = "Matches your search terms."


def _plain(text: str) -> str:
    """Lower case, one space between words, straight quotes and hyphens."""
    text = text.translate(str.maketrans({"‘": "'", "’": "'", "“": '"',
                                         "”": '"', "–": "-", "—": "-"}))
    return re.sub(r"\s+", " ", text).strip().lower()


class BudgetSpent(Exception):
    """Our own daily token budget is used up."""


def check_reply(conn, raw: str, seen: set[int]) -> tuple[AgentReply | None, list[str]]:
    """Returns the parsed answer and what is wrong with it. Unsupported claims are separate:
    see unsupported_claims."""
    try:
        reply = AgentReply.model_validate_json(raw)
    except ValidationError as exc:
        return None, [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:5]]
    problems = []
    for rec in reply.recommendations:
        if rec.job_id not in seen:
            problems.append(f"job_id {rec.job_id} was not returned by any tool")
            continue
        text = conn.execute("select description_text from jobs where id = %s", (rec.job_id,)).fetchone()[0]
        if _plain(rec.evidence).strip(" .\"'") not in _plain(text):
            problems.append(f"the evidence for job_id {rec.job_id} is not a phrase from that posting's"
                            " snippet or description (the title does not count): copy one exactly")
    return reply, problems


def unsupported_claims(conn, reply: AgentReply, seen: set[int]) -> dict[int, list[str]]:
    """{job id: claims the posting does not support}."""
    found = {}
    for rec in reply.recommendations:
        if rec.job_id in seen and rec.claims:
            failed = verify.failed_claims(verify.load_job(conn, rec.job_id), rec.claims)
            if failed:
                found[rec.job_id] = failed
    return found


def direct_search(ctx: tools.Context, text: str) -> list[int]:
    """Used when the model gave us nothing: search for the user's own words."""
    mode, vector = tools.SEARCH_MODE, None
    try:
        vector = list(ctx.embed(text[:300]))
    except Exception as exc:
        log.warning("query embedding failed, using keyword search: %s", type(exc).__name__)
        mode = "keyword"
    ids = [hit.job_id for hit in search(ctx.conn, text, vector, {}, 5, mode)]
    ctx.seen.update(ids)
    return ids


def cards(conn, picks: list[tuple[int, str, str]]) -> list[dict]:
    """Everything about a job on screen comes from the database, never from the model."""
    result = []
    for job_id, why, evidence in picks:
        row = conn.execute(
            "select j.title, c.name, j.location_raw, j.level, j.is_remote, j.apply_url, j.source,"
            " j.source_url, j.status from jobs j join companies c on c.id = j.company_id"
            " where j.id = %s", (job_id,)).fetchone()
        if row:
            keys = ("title", "company", "location", "level", "is_remote", "apply_url", "source",
                    "source_url", "status")
            result.append({"job_id": job_id, "why": why, "evidence": evidence, **dict(zip(keys, row))})
    return result


def _history_messages(conn, session_id: str) -> list[llm.Message]:
    messages = []
    for role, content in store.history(conn, session_id):
        text = content.get("text", "")
        if content.get("clarifying_question"):
            text += "\n" + content["clarifying_question"]
        if content.get("cards"):  # lets "tell me about the second one" work
            shown = "; ".join(f"job_id {c['job_id']}: {c['title']} at {c['company']}" for c in content["cards"])
            text += f"\n[Jobs shown to the user, in order: {shown}]"
        messages.append(llm.Message(role, text))
    return messages


def run_turn(conn, session_id: str, user_text: str, *, generate=llm.generate, embed=None,
             check_claims: bool = True, trace: dict | None = None) -> dict:
    """`trace`, if given, receives the model's first well-formed answer before any check on its
    ids, quotes or claims, which is what the grounding evaluation compares against."""
    messages = _history_messages(conn, session_id) + [llm.Message("user", user_text)]
    ctx = tools.Context(conn, session_id, store.seen_job_ids(conn, session_id))
    if embed is not None:
        ctx.embed = embed
    trace = {} if trace is None else trace
    trace.update(first_answer=None, rejections=[], steps=0, hit_step_limit=False)

    def ask(**options) -> llm.LLMResult:
        if store.tokens_today(conn) >= settings.daily_token_budget:
            raise BudgetSpent()
        profile = json.dumps(store.load_profile(conn, session_id), ensure_ascii=False)
        system = f"{PROMPT}\nSaved profile of this user: {profile}\n"
        started = time.perf_counter()
        try:
            result = generate(messages, system=system, **options)
        except Exception as exc:
            store.log_llm_call(conn, session_id, "unknown", int((time.perf_counter() - started) * 1000),
                               False, PROMPT_VERSION, error=f"{type(exc).__name__}: {exc}"[:500])
            raise
        store.log_llm_call(conn, session_id, result.model, int((time.perf_counter() - started) * 1000),
                           True, PROMPT_VERSION, result.input_tokens, result.output_tokens)
        return result

    reply, outcome, repairs, removed = None, "ok", 0, {}
    try:
        for step in range(MAX_STEPS):
            result = ask(tools=tools.DECLARATIONS)
            trace["steps"] = step + 1
            if not result.tool_calls:
                break
            messages.append(result.message)
            for call in result.tool_calls:
                output = tools.execute(ctx, call.name, call.args)
                messages.append(llm.Message("tool", tool_name=call.name, call_id=call.id, result=output))
        else:  # no more tool calls: answer with what has been found
            trace["hit_step_limit"] = True

        schema = AgentReply.model_json_schema()
        claims_retried = False
        for attempt in range(MAX_REPAIRS + 1):
            raw = ask(schema=schema).text
            candidate, problems = check_reply(conn, raw, ctx.seen)
            if trace["first_answer"] is None and candidate:
                trace["first_answer"] = candidate.model_dump()
            claims = unsupported_claims(conn, candidate, ctx.seen) if candidate and check_claims else {}
            # unsupported claims get one retry; after that the explanation is dropped
            if not problems and (not claims or claims_retried or attempt == MAX_REPAIRS):
                reply, removed = candidate, claims
                break
            if claims:
                claims_retried = True
                problems = problems + [f"for job_id {job_id}, the posting does not support: "
                                       + ", ".join(failed) for job_id, failed in claims.items()]
            log.info("answer rejected: %s", problems)
            trace["rejections"].append(problems)
            repairs = attempt + 1
            messages += [llm.Message("assistant", raw or "(empty)"),
                         llm.Message("user", "That answer was rejected: " + "; ".join(problems)
                                     + ". Return a corrected answer.")]
        else:
            outcome = "invalid_answer"
    except BudgetSpent:
        outcome = "budget"
    except (llm.ModelUnavailable, llm.RateLimited, llm.DailyQuotaExhausted) as exc:
        outcome = "daily_limit" if isinstance(exc, llm.DailyQuotaExhausted) else "model_busy"

    if reply:
        unique = {r.job_id: r for r in reply.recommendations}  # no job twice
        text, question = reply.message, reply.clarifying_question
        shown = cards(conn, [(r.job_id, NEUTRAL_WHY, "") if r.job_id in removed
                             else (r.job_id, r.why, r.evidence) for r in unique.values()])
    else:  # fall back to plain search results, without any model-written claims
        question = None
        found = ctx.found[:5] or direct_search(ctx, user_text)
        shown = cards(conn, [(job_id, NEUTRAL_WHY, "") for job_id in found])
        reason = {"invalid_answer": "I could not write a reliable explanation.",
                  "model_busy": "AI explanations are temporarily unavailable: the model is busy.",
                  "daily_limit": "AI explanations are unavailable: the free daily limit is used up.",
                  "budget": "AI explanations are unavailable: today's usage budget is spent."}[outcome]
        text = reason + (" Here is what the search found." if shown else " Please try again.")

    trace["seen"], trace["found"] = sorted(ctx.seen), list(ctx.found)
    store.save_message(conn, session_id, "user", {"text": user_text})
    store.save_message(conn, session_id, "assistant", {
        "text": text, "clarifying_question": question, "outcome": outcome, "repairs": repairs,
        "claims_removed": len(removed),
        "cards": [{k: c[k] for k in ("job_id", "title", "company")} for c in shown],
        "seen_job_ids": sorted(ctx.seen)})
    return {"message": text, "cards": shown, "clarifying_question": question,
            "outcome": outcome, "repairs": repairs, "claims_removed": len(removed)}
