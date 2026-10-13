"""Founder-in-the-loop block refinement: "@Block + preference" → the block's agent rewrites it → the council
re-assesses → everything that depends on it re-syncs.

Before G2 (actions not yet approved): the 5 seats re-score only the refined block, a new verdict round is computed in
code. After G2 (actions approved/executed): a full council round runs again, then the pilot summary and the report
are regenerated. Bounded (rule 5): one refinement at a time per session, at most MAX_VERSIONS versions per block."""
import asyncio
import json
import logging
import re
from typing import Any

from sqlalchemy import func, select

from app.agent import factories, pipeline, prompts
from app.agent.common import label, make_agent, run_agent
from app.db import SessionLocal
from app.events import emit
from app.models import (BMC_KEYS, ActionItem, BmcBlock, ChatMessage, CouncilReview, CouncilVerdict, StartupSession,
                        WorkbuddyTask)
from app.schemas.agents import BlockRescoreOut, RefinedBlockOut
from app.workbuddy import queue

log = logging.getLogger("startupbuddy.refine")
MAX_VERSIONS = 6  # v1 from the pipeline + 5 founder refinements per block
PRE_G2 = ("deliverables", "advisor", "gate_g2")
POST_G2 = ("actions", "done")
# Knock-on effects: when a block changes, these blocks may no longer match it (flagged, not auto-rewritten).
DEPENDS: dict[str, list[str]] = {
    "customer_segments": ["value_propositions", "channels", "customer_relationships", "revenue_streams"],
    "value_propositions": ["channels", "customer_relationships", "revenue_streams"],
    "channels": ["revenue_streams", "cost_structure"],
    "customer_relationships": ["cost_structure"],
    "key_activities": ["key_resources", "cost_structure"],
    "key_resources": ["cost_structure"],
    "key_partners": ["key_activities", "cost_structure"],
    "revenue_streams": ["cost_structure"],
    "cost_structure": ["revenue_streams"],
}
NAME = {k: label(k).split(" ", 1)[1] for k in BMC_KEYS}
ALIAS = {**{k: k for k in BMC_KEYS}, **{NAME[k].lower().replace(" ", ""): k for k in BMC_KEYS},
         "segments": "customer_segments", "customers": "customer_segments", "value": "value_propositions",
         "vp": "value_propositions", "relationships": "customer_relationships", "activities": "key_activities",
         "resources": "key_resources", "partners": "key_partners", "revenue": "revenue_streams",
         "costs": "cost_structure", "cost": "cost_structure"}
_running: dict[str, dict[str, Any]] = {}  # session_id → {"key", "mode", "stage", "task"}


class RefineError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def status(sid: str) -> dict[str, Any] | None:
    r = _running.get(sid)
    if not r or r["task"].done():
        return None
    return {k: r[k] for k in ("key", "mode", "stage")}


def parse_mention(text: str) -> tuple[str, str] | None:
    """'@Value Propositions make it halal-certified' / '@revenue_streams ...' → (key, instruction)."""
    m = re.match(r"\s*@([A-Za-z_]+(?:[ _][A-Za-z]+)?)[\s:,-]*(.*)", text, re.S)
    if not m:
        return None
    head, rest = m.group(1), m.group(2)
    two = head.lower().replace("_", "").replace(" ", "")
    if two in ALIAS:
        return ALIAS[two], rest.strip()
    first = head.split(" ")[0].lower().replace("_", "")  # "@revenue make it…" captured "revenue make"
    if first in ALIAS:
        return ALIAS[first], (head.split(" ", 1)[1] + " " + rest).strip() if " " in head else rest.strip()
    return None


async def request(sid: str, key: str, instruction: str, channel: str = "web") -> dict[str, Any]:
    """Validate and start a refinement in the background; progress streams to the feed."""
    instruction = instruction.strip()
    if key not in BMC_KEYS:
        raise RefineError(400, f"unknown block {key!r}")
    if len(instruction) < 3:
        raise RefineError(422, f"Tell me how you'd like {NAME[key]} to change, e.g. “@{NAME[key]} focus on students”.")
    async with SessionLocal() as db:
        s = await db.get(StartupSession, sid)
        if not s:
            raise RefineError(404, "session not found")
        phase = s.phase
        versions = (await db.execute(select(func.count()).select_from(BmcBlock).where(
            BmcBlock.session_id == sid, BmcBlock.key == key, BmcBlock.status == "done"))).scalar_one()
    if phase not in PRE_G2 + POST_G2:
        raise RefineError(409, "Blocks can be refined once the council has reviewed the canvas.")
    if status(sid):
        raise RefineError(409, f"I'm still refining {NAME[_running[sid]['key']]}. One change at a time, please.")
    if versions == 0:
        raise RefineError(409, f"{NAME[key]} hasn't been written yet.")
    if versions >= MAX_VERSIONS:
        raise RefineError(409, f"{NAME[key]} has reached {MAX_VERSIONS} versions. Let's test it in the real world first.")
    hit = pipeline._illegal_hit(instruction)
    if hit:
        raise RefineError(422, f"I can't plan around “{hit[1]}”: it's illegal in Malaysia under the {hit[0]}.")
    mode = "rescore" if phase in PRE_G2 else "retriage"
    text = f"@{NAME[key]} {instruction}"
    async with SessionLocal() as db:
        db.add(ChatMessage(session_id=sid, role="user", content=text, channel=channel))
        await db.commit()
    await emit(sid, "founder", "chat", text, detail={"role": "user", "channel": channel, "refine": key})
    _running[sid] = {"key": key, "mode": mode, "stage": "rewrite",
                     "task": asyncio.create_task(_run(sid, key, instruction, mode, channel))}
    return {"ok": True, "block": key, "mode": mode,
            "message": "Re-scoring this block with the council" if mode == "rescore"
            else "Checkpoint 2 has passed, so the full council will review again"}


async def _latest(db, sid: str, key: str) -> BmcBlock | None:
    return (await db.execute(select(BmcBlock).where(BmcBlock.session_id == sid, BmcBlock.key == key, BmcBlock.status == "done")
                             .order_by(BmcBlock.round.desc()).limit(1))).scalar_one_or_none()


async def _verdict(db, sid: str) -> CouncilVerdict | None:
    return (await db.execute(select(CouncilVerdict).where(CouncilVerdict.session_id == sid)
                             .order_by(CouncilVerdict.round.desc()).limit(1))).scalar_one_or_none()


async def _latest_reviews(db, sid: str) -> list[CouncilReview]:
    rows = (await db.execute(select(CouncilReview).where(CouncilReview.session_id == sid)
                             .order_by(CouncilReview.round))).scalars().all()
    return list({r.seat: r for r in rows}.values())


async def _run(sid: str, key: str, instruction: str, mode: str, channel: str) -> None:
    try:
        await _refine(sid, key, instruction, mode, channel)
    except Exception as e:
        log.exception("refinement failed")
        await emit(sid, key, "error", f"😓 I couldn't refine {NAME[key]} this time ({type(e).__name__}). Your previous version is kept.",
                   target=key)
        await _reply(sid, f"😓 Sorry, refining **{NAME[key]}** didn't work this time. Nothing changed; please try again.", channel)


async def _rewrite(sid: str, key: str, instruction: str) -> tuple[dict[str, Any], RefinedBlockOut, int] | None:
    async with SessionLocal() as db:
        prev = await _latest(db, sid, key)
        rnd = ((await db.execute(select(func.max(BmcBlock.round)).where(BmcBlock.session_id == sid, BmcBlock.key == key)))
               .scalar_one() or 0) + 1
        reviews = await _latest_reviews(db, sid)
        verdict = await _verdict(db, sid)
        row = BmcBlock(session_id=sid, key=key, round=rnd, status="thinking", content=prev.content, instruction=instruction)
        db.add(row)
        await db.commit()
        prev_content, row_id = prev.content, row.id
    version = rnd + 1
    await emit(sid, key, "thought", f"✍️ {label(key)} is rewriting with your input (v{version})…", target=key,
               detail={"refine": True, "version": version})
    ctx = await pipeline._context(sid)
    ctx["founder_refinement"] = {
        "instruction": instruction, "current_version": prev_content,
        "council_mean_score_for_this_block": (verdict.block_means or {}).get(key) if verdict else None,
        "council_feedback": [{"seat": r.seat, "score_for_this_block": r.scores.get(key), "improve": r.improve[:4],
                              "risks": r.risks[:3]} for r in reviews],
    }
    agent = make_agent(key, prompts.BMC_AGENT.format(block_desc=prompts.BMC[key]) + prompts.REFINE, RefinedBlockOut,
                       sid, key, [factories.knowledge_tool()])
    out: RefinedBlockOut | None = None
    for attempt in (1, 2):
        try:
            prompt = json.dumps(ctx, ensure_ascii=False, default=str)
            if attempt == 2:
                prompt += "\n\nRetry: answer directly from the context; call search_knowledge at most once."
                await emit(sid, key, "thought", f"🔁 {label(key)} is taking another pass", target=key)
            out = await run_agent(agent, prompt, RefinedBlockOut, sid, key)
            break
        except Exception:
            continue
    async with SessionLocal() as db:
        row = await db.get(BmcBlock, row_id)
        if out is None:
            await db.delete(row)  # the previous version stays the latest
            await db.commit()
            return None
        content = out.model_dump(exclude={"evidence", "change_note"})
        row.content, row.change_note, row.status = content, out.change_note[:500], "done"
        await db.commit()
    await pipeline._save_evidence(sid, key, out.evidence, f"{key} v{version}")
    return content, out, version


async def _flag_dependents(sid: str, key: str, version: int, note: str) -> list[str]:
    flagged = []
    async with SessionLocal() as db:
        for dep in DEPENDS.get(key, []):
            b = await _latest(db, sid, dep)
            if b:
                b.stale_reason = f"{NAME[key]} changed in v{version}: {note}"[:400]
                flagged.append(dep)
        await db.commit()
    if flagged:
        await emit(sid, "pipeline", "thought",
                   f"🔗 Knock-on check: {', '.join(NAME[k] for k in flagged)} may need a look now that {NAME[key]} changed",
                   detail={"stale": flagged, "because": key})
    return flagged


async def _rescore(sid: str, key: str, prev_content: dict[str, Any], new_content: dict[str, Any]) -> dict[str, Any]:
    """Pre-G2: each seat re-scores only the refined block (parallel); code recomputes the verdict."""
    ctx = await pipeline._context(sid)
    async with SessionLocal() as db:
        reviews = await _latest_reviews(db, sid)
        rnd = ((await db.execute(select(func.max(CouncilVerdict.round)).where(CouncilVerdict.session_id == sid))).scalar_one() or 0) + 1

    async def seat(r: CouncilReview) -> CouncilReview:
        prompt = json.dumps({**ctx, "block_under_review": key, "previous_version": prev_content, "new_version": new_content,
                             "your_previous_review": {"score_for_this_block": r.scores.get(key), "verdict": r.verdict,
                                                      "improve": r.improve[:4], "risks": r.risks[:3]}},
                            ensure_ascii=False, default=str)
        agent = make_agent(f"council_{r.seat}", prompts.COUNCIL_AGENT.format(seat_desc=prompts.COUNCIL[r.seat]) + prompts.RESCORE,
                           BlockRescoreOut, sid, f"council_{r.seat}")
        scores, verdict, strengths, risks = dict(r.scores), r.verdict, list(r.strengths), list(r.risks)
        try:
            out = await run_agent(agent, prompt, BlockRescoreOut, sid, f"council_{r.seat}", timeout_s=90)
            before = scores.get(key)
            scores[key], verdict = out.score, out.verdict
            note = f"{NAME[key]} (refined): {out.reason}"
            (strengths if out.score >= 4 else risks).insert(0, note)
            await emit(sid, f"council_{r.seat}", "done", f"{NAME[key]}: {before if before is not None else '–'} → {out.score}/5 · {out.reason}",
                       target=f"council_{r.seat}", detail={"block": key, "before": before, "after": out.score})
        except Exception:
            await emit(sid, f"council_{r.seat}", "fallback", f"⏳ I kept my previous score for {NAME[key]}", target=f"council_{r.seat}")
        return CouncilReview(session_id=sid, seat=r.seat, round=rnd, scores=scores, strengths=strengths[:8], risks=risks[:8],
                             must_verify=r.must_verify, improve=r.improve, verdict=verdict)

    new_rows = await asyncio.gather(*(seat(r) for r in reviews))
    agg = factories.aggregate([pipeline.review_from_row(r) for r in new_rows])
    async with SessionLocal() as db:
        db.add_all(new_rows)
        db.add(CouncilVerdict(session_id=sid, round=rnd, trigger=f"founder refined {key} (block re-score)", **agg))
        await db.commit()
    return agg


async def _refresh_report(sid: str) -> None:
    """Keep the WorkBuddy report in sync: rewrite a still-queued report task, else queue a new one."""
    from app.routers.sessions import build_report_markdown
    md = (await build_report_markdown(sid))[:30000]
    async with SessionLocal() as db:
        queued = (await db.execute(select(WorkbuddyTask).where(WorkbuddyTask.session_id == sid, WorkbuddyTask.skill == "report_builder",
                                                               WorkbuddyTask.status == "queued"))).scalars().all()
        for t in queued:
            t.inputs = {**t.inputs, "session_summary_markdown": md}
        await db.commit()
    if queued:
        await emit(sid, "workbuddy", "thought", "📝 Updated the report task WorkBuddy hasn't started yet", target="workbuddy")
        return
    if await queue.worker_online():
        await queue.enqueue(sid, "report_builder", {"session_summary_markdown": md,
                                                   "format": "Markdown only (StartupBuddy renders the DOCX)"}, deadline_s=600)
    else:  # rule 4: never wait on WorkBuddy; render our own report so the DOCX is never stale
        await queue._store_report_docx(sid, None, {"title": "StartupBuddy Report (updated)", "report_markdown": md})


def _fmt(x: float | None) -> str:
    return "–" if x is None else f"{x:.1f}"


async def _refine(sid: str, key: str, instruction: str, mode: str, channel: str) -> None:
    async with SessionLocal() as db:
        v0 = await _verdict(db, sid)
        prev = await _latest(db, sid, key)
        prev_content = prev.content
    before, overall_before = (v0.block_means or {}).get(key) if v0 else None, v0.overall if v0 else None

    res = await _rewrite(sid, key, instruction)
    if res is None:
        await emit(sid, key, "error", f"😓 {label(key)} couldn't produce a new version. Your previous version is kept.", target=key)
        await _reply(sid, f"😓 I couldn't rewrite **{NAME[key]}** just now. Your previous version is kept; please try again.", channel)
        return
    content, out, version = res
    await emit(sid, key, "done", f"✨ {NAME[key]} v{version}: {out.change_note}", target=key,
               detail={"refine": True, "version": version, "instruction": instruction})
    stale = await _flag_dependents(sid, key, version, out.change_note)

    _running[sid]["stage"] = "council"
    if mode == "rescore":
        await emit(sid, "council", "handoff", f"⚖️ The council is re-scoring {NAME[key]}", target="council", detail={"block": key})
        agg = await _rescore(sid, key, prev_content, content)
    else:
        async with SessionLocal() as db:
            rnd = ((await db.execute(select(func.max(CouncilVerdict.round)).where(CouncilVerdict.session_id == sid))).scalar_one() or 0) + 1
        await emit(sid, "council", "handoff",
                   f"⚖️ Checkpoint 2 has passed, so the full council is reviewing the updated canvas again (round {rnd + 1})",
                   target="council", detail={"block": key, "round": rnd})
        agg = await pipeline._phase_council(sid, rnd, trigger=f"founder refined {key} after Checkpoint 2 (full re-triage)",
                                            set_phase=False)
    after = agg["block_means"].get(key)
    delta = round(after - before, 2) if after is not None and before is not None else None
    arrow = "📈" if (delta or 0) > 0 else "📉" if (delta or 0) < 0 else "➖"
    verdict_line = (f" · verdict {overall_before.upper()} → {agg['overall'].upper()}" if overall_before and overall_before != agg["overall"]
                    else f" · verdict stays {agg['overall'].upper()}")
    await emit(sid, "council", "done", f"{arrow} {NAME[key]} {_fmt(before)} → {_fmt(after)}"
               + (f" ({delta:+.1f})" if delta is not None else "") + verdict_line, target="council",
               detail={**agg, "refined_block": key, "before": before, "after": after, "delta": delta,
                       "overall_before": overall_before, "mode": mode, "version": version})

    _running[sid]["stage"] = "sync"
    # Actions that came from this block (or a block it affects) may be out of date: tell the founder, never auto-change them.
    async with SessionLocal() as db:
        acts = (await db.execute(select(ActionItem).where(ActionItem.session_id == sid,
                                                          ActionItem.source_agent.in_([key, *stale])))).scalars().all()
        phase = (await db.get(StartupSession, sid)).phase
    if acts:
        await emit(sid, "advisor", "thought", f"📌 Worth a second look after this change: {', '.join(a.title for a in acts[:3])}",
                   target="advisor", detail={"actions": [a.id for a in acts]})
    if mode == "retriage" and phase == "done":
        await pipeline._pilot_summary(sid)
    await _refresh_report(sid)
    reply = (f"✨ **{NAME[key]}** is now v{version}: {out.change_note}\n\n"
             f"Council score {_fmt(before)} → **{_fmt(after)}**/5" + (f" ({delta:+.1f})" if delta is not None else "")
             + f", overall verdict **{agg['overall'].upper()}**.")
    if stale:
        reply += f"\n\n🔗 This may affect {', '.join(NAME[k] for k in stale)}. Tap one and choose *Refine* to bring it in line."
    if mode == "retriage":
        reply += "\n\nBecause your actions were already approved, the whole council reviewed again and your report was refreshed."
    await _reply(sid, reply, channel)


async def _reply(sid: str, text: str, channel: str) -> None:
    async with SessionLocal() as db:
        db.add(ChatMessage(session_id=sid, role="assistant", content=text, channel=channel))
        await db.commit()
    await emit(sid, "session_assistant", "chat", text, detail={"role": "assistant", "channel": channel})
