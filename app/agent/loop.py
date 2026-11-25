"""One conversation turn: let the model use tools, then check its answer before showing it."""
import json
import logging
import re
import time
from pathlib import Path

from pydantic import ValidationError

from app import llm
from app.agent import store, tools
from app.agent.schemas import AgentReply

log = logging.getLogger(__name__)

MAX_STEPS = 5       # model calls that may use tools, per turn
MAX_REPAIRS = 2     # extra attempts when the final answer fails the checks
PROMPT_VERSION = "v1"
PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.md").read_text()
NEUTRAL_WHY = "Matches your search terms."


def _plain(text: str) -> str:
    """Lower case, one space between words, straight quotes and hyphens."""
    text = text.translate(str.maketrans({"‘": "'", "’": "'", "“": '"',
                                         "”": '"', "–": "-", "—": "-"}))
    return re.sub(r"\s+", " ", text).strip().lower()


def check_reply(conn, raw: str, seen: set[int]) -> tuple[AgentReply | None, list[str]]:
    """Returns the parsed answer and what is wrong with it (empty list: show it)."""
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


def run_turn(conn, session_id: str, user_text: str, *, generate=llm.generate, embed=None) -> dict:
    messages = _history_messages(conn, session_id) + [llm.Message("user", user_text)]
    ctx = tools.Context(conn, session_id, store.seen_job_ids(conn, session_id))
    if embed is not None:
        ctx.embed = embed

    def ask(**options) -> llm.LLMResult:
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

    reply, outcome, repairs = None, "ok", 0
    try:
        for _ in range(MAX_STEPS):
            result = ask(tools=tools.DECLARATIONS)
            if not result.tool_calls:
                break
            messages.append(result.message)
            for call in result.tool_calls:
                output = tools.execute(ctx, call.name, call.args)
                messages.append(llm.Message("tool", tool_name=call.name, call_id=call.id, result=output))
        else:
            outcome = "step_limit"

        if outcome == "ok":
            schema = AgentReply.model_json_schema()
            for attempt in range(MAX_REPAIRS + 1):
                raw = ask(schema=schema).text
                candidate, problems = check_reply(conn, raw, ctx.seen)
                if not problems:
                    reply = candidate
                    break
                log.info("answer rejected: %s", problems)
                repairs = attempt + 1
                messages += [llm.Message("assistant", raw or "(empty)"),
                             llm.Message("user", "That answer was rejected: " + "; ".join(problems)
                                         + ". Return a corrected answer.")]
            else:
                outcome = "invalid_answer"
    except (llm.ModelUnavailable, llm.RateLimited, llm.DailyQuotaExhausted) as exc:
        outcome = "daily_limit" if isinstance(exc, llm.DailyQuotaExhausted) else "model_busy"

    if reply:
        unique = {r.job_id: r for r in reply.recommendations}  # no job twice
        text, question = reply.message, reply.clarifying_question
        shown = cards(conn, [(r.job_id, r.why, r.evidence) for r in unique.values()])
    else:  # fall back to plain search results, without any model-written claims
        question = None
        shown = cards(conn, [(job_id, NEUTRAL_WHY, "") for job_id in ctx.found[:5]])
        reason = {"step_limit": "I could not finish working through your request.",
                  "invalid_answer": "I could not write a reliable explanation.",
                  "model_busy": "The language model is busy right now.",
                  "daily_limit": "The free daily limit of the language model is used up."}[outcome]
        text = reason + (" Here is what the search found." if shown else " Please try again.")

    store.save_message(conn, session_id, "user", {"text": user_text})
    store.save_message(conn, session_id, "assistant", {
        "text": text, "clarifying_question": question, "outcome": outcome, "repairs": repairs,
        "cards": [{k: c[k] for k in ("job_id", "title", "company")} for c in shown],
        "seen_job_ids": sorted(ctx.seen)})
    return {"message": text, "cards": shown, "clarifying_question": question,
            "outcome": outcome, "repairs": repairs}
