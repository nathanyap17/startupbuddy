"""StartupPipeline: Phase 1 problem → G1 → Phase 2 BMC (3 waves) → Phase 3 council (5 parallel,
deterministic aggregation) → WorkBuddy report + Phase 4 advisor → G2 → approved actions.

Gates live in the DB (phase) and wake via in-process events (single Cloud Run instance)."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.agent import factories
from app.agent.common import run_agent
from app.config import settings
from app.db import SessionLocal
from app.events import emit
from app.mcp import gws
from app.models import (ActionItem, BmcBlock, CouncilReview, CouncilVerdict, EvidenceItem, ProblemStatement,
                        StartupSession)
from app.rag.search import search as kb_search
from app.schemas.agents import ActionsOut, BlockOut, EvidenceOut, ProblemOut, ReviewOut
from app.tools import places
from app.workbuddy import queue

log = logging.getLogger("startupbuddy.pipeline")
WAVES = [["customer_segments", "value_propositions"],
         ["channels", "customer_relationships", "key_activities", "key_resources", "key_partners"],
         ["revenue_streams", "cost_structure"]]
SEATS = ["customer", "ceo", "investor", "cfo", "mentor"]
_gates: dict[str, asyncio.Event] = {}
_running: dict[str, asyncio.Task] = {}


def gate_event(session_id: str) -> asyncio.Event:
    return _gates.setdefault(session_id, asyncio.Event())


def start(session_id: str) -> None:
    if session_id in _running and not _running[session_id].done():
        return
    _running[session_id] = asyncio.create_task(_run(session_id))


async def _set_phase(session_id: str, phase: str, error: str | None = None) -> None:
    async with SessionLocal() as db:
        s = await db.get(StartupSession, session_id)
        s.phase = phase
        if error:
            s.error = error
        await db.commit()
    await emit(session_id, "pipeline", "phase", f"Phase → {phase}", detail={"phase": phase})


async def _save_evidence(session_id: str, scope: str, items: list[EvidenceOut], produced_by: str) -> None:
    """Rule 2 enforced in code: unsupported labels are downgraded to needs_verification."""
    async with SessionLocal() as db:
        for e in items:
            label = e.label
            if label == "sourced" and not (e.source_url and e.source_url.startswith("http")):
                label = "needs_verification"
            if label == "estimated" and not e.method:
                label = "needs_verification"
            db.add(EvidenceItem(session_id=session_id, scope=scope, claim=e.claim[:500], value=e.value,
                                label=label, source_url=e.source_url if label == "sourced" else None,
                                method=e.method if label == "estimated" else None, produced_by=produced_by))
        await db.commit()


async def _wait_gate(session_id: str, phase: str) -> None:
    ev = gate_event(session_id)
    ev.clear()
    await _set_phase(session_id, phase)
    while True:
        await ev.wait()
        ev.clear()
        async with SessionLocal() as db:
            s = await db.get(StartupSession, session_id)
            if s.phase != phase:
                return


# ---------------------------------------------------------------- Phase 1
async def _phase_problem(s: StartupSession) -> None:
    sid = s.id
    await _set_phase(sid, "problem")
    geo = None
    try:
        geo = await places.geocode(s.location_text)
    except Exception as e:
        await emit(sid, "problem_coordinator", "error", f"Geocoding failed: {e}", target="problem")
    if geo:
        async with SessionLocal() as db:
            row = await db.get(StartupSession, sid)
            row.lat, row.lng = geo["lat"], geo["lng"]
            await db.commit()
        await emit(sid, "problem_coordinator", "tool_result", f"Located {geo['name']} ({geo['address']})",
                   target="problem", detail=geo)

    # WorkBuddy desk research runs in parallel with local grounding.
    task_id = await queue.enqueue(sid, "desk_research", {
        "intent": s.intent, "location": s.location_text,
        "questions": ["Demand and customer behaviour for this idea in this Malaysian location",
                      "Typical prices and costs in RM", "Licences/registration needed (SSM, local council, food/halal if relevant)",
                      "Trends or recent news (why now)"]})

    competitors: list[dict[str, Any]] = []
    if geo:
        try:
            query = await _competitor_query(s.intent)
            competitors = await places.nearby_competitors(query, geo["lat"], geo["lng"], 1000)
            within = [c for c in competitors if c["distance_km"] <= 1.0]
            await emit(sid, "problem_coordinator", "tool_result",
                       f"Google Maps: {len(within)} '{query}' competitors within 1 km", target="problem",
                       detail={"competitors": competitors[:10]})
        except Exception as e:
            await emit(sid, "problem_coordinator", "error", f"Places search failed: {e}", target="problem")
    kb = await kb_search(f"{s.intent} {s.location_text} licence registration", k=4)

    research = await queue.wait_for(task_id, timeout_s=min(240, settings.workbuddy_task_deadline_s))
    if research is None:
        await emit(sid, "problem_coordinator", "fallback",
                   "WorkBuddy desk research not available in time; continuing with Maps + knowledge base",
                   target="problem")
    else:
        await _save_evidence(sid, "problem", [EvidenceOut(**f) for f in research.get("findings", [])][:12],
                             "workbuddy:desk_research")

    prompt = json.dumps({
        "intent": s.intent, "location": s.location_text, "geocode": geo,
        "nearby_competitors_google_maps": competitors[:12],
        "knowledge_excerpts": kb, "workbuddy_desk_research": research,
    }, ensure_ascii=False, default=str)
    agent = factories.coordinator(sid, geo and geo["lat"], geo and geo["lng"])
    out = await run_agent(agent, prompt, ProblemOut, sid, "problem", timeout_s=150)
    async with SessionLocal() as db:
        db.add(ProblemStatement(session_id=sid, statement=out.statement, target_user=out.target_user,
                                pain=out.pain, why_now=out.why_now,
                                details={"demand_signals": out.demand_signals,
                                         "competition_summary": out.competition_summary,
                                         "differentiation_hypothesis": out.differentiation_hypothesis,
                                         "competitors": competitors[:10]}))
        await db.commit()
    await _save_evidence(sid, "problem", out.evidence, "problem_coordinator")
    await emit(sid, "problem_coordinator", "done", "Problem statement ready for your confirmation (G1)",
               target="problem", detail={"statement": out.statement})


async def _competitor_query(intent: str) -> str:
    """Short Maps query from the intent (cheap heuristic, no LLM)."""
    import re
    m = re.search(r"(?:sell|open|start|run|build)\s+(?:a\s+|an\s+)?(.+?)(?:\s+(?:near|in|at|around)\b|$)", intent, re.I)
    q = (m.group(1) if m else intent).strip(" .")
    return " ".join(q.split()[:5])


# ---------------------------------------------------------------- Phase 2
async def _context(sid: str) -> dict[str, Any]:
    async with SessionLocal() as db:
        s = await db.get(StartupSession, sid)
        p = (await db.execute(select(ProblemStatement).where(ProblemStatement.session_id == sid)
                              .order_by(ProblemStatement.version.desc()).limit(1))).scalar_one()
        blocks = (await db.execute(select(BmcBlock).where(BmcBlock.session_id == sid))).scalars().all()
    latest: dict[str, Any] = {}
    for b in sorted(blocks, key=lambda b: b.round):
        if b.status == "done":
            latest[b.key] = b.content
    return {"intent": s.intent, "location": s.location_text,
            "problem": {"statement": p.statement, "target_user": p.target_user, "pain": p.pain,
                        "why_now": p.why_now, **p.details}, "canvas_so_far": latest}


async def _run_block(sid: str, key: str, rnd: int, notes: list[str] | None = None) -> None:
    async with SessionLocal() as db:
        b = (await db.execute(select(BmcBlock).where(BmcBlock.session_id == sid, BmcBlock.key == key,
                                                     BmcBlock.round == rnd))).scalar_one_or_none()
        if not b:
            b = BmcBlock(session_id=sid, key=key, round=rnd, status="thinking")
            db.add(b)
        b.status = "thinking"
        await db.commit()
    await emit(sid, key, "thought", f"Working on {key.replace('_', ' ')}", target=key)
    ctx = await _context(sid)
    if notes:
        ctx["council_notes_to_address"] = notes
    try:
        out = await run_agent(factories.bmc_agent(sid, key), json.dumps(ctx, ensure_ascii=False, default=str),
                              BlockOut, sid, key)
        content, status = out.model_dump(exclude={"evidence"}), "done"
        await _save_evidence(sid, key, out.evidence, key)
    except Exception as e:
        content, status = {"summary": f"(agent failed: {type(e).__name__})", "items": [], "assumptions": []}, "failed"
    async with SessionLocal() as db:
        b = (await db.execute(select(BmcBlock).where(BmcBlock.session_id == sid, BmcBlock.key == key,
                                                     BmcBlock.round == rnd))).scalar_one()
        b.content, b.status = content, status
        await db.commit()


async def _phase_bmc(sid: str) -> None:
    await _set_phase(sid, "bmc")
    for i, wave in enumerate(WAVES, 1):
        await emit(sid, "pipeline", "handoff", f"BMC wave {i}: {', '.join(wave)}", detail={"wave": i, "blocks": wave})
        await asyncio.gather(*(_run_block(sid, k, 0) for k in wave))


# ---------------------------------------------------------------- Phase 3
async def _phase_council(sid: str) -> dict[str, Any]:
    await _set_phase(sid, "council")
    ctx = json.dumps(await _context(sid), ensure_ascii=False, default=str)

    async def seat(name: str) -> ReviewOut | None:
        try:
            r = await run_agent(factories.council_agent(sid, name), ctx, ReviewOut, sid, f"council_{name}")
        except Exception:
            return None
        async with SessionLocal() as db:
            db.add(CouncilReview(session_id=sid, seat=name, round=0,
                                 scores={x.block: x.score for x in r.scores}, strengths=r.strengths,
                                 risks=r.risks, must_verify=r.must_verify, improve=r.improve, verdict=r.verdict))
            await db.commit()
        return r

    reviews = [r for r in await asyncio.gather(*(seat(n) for n in SEATS)) if r]
    agg = factories.aggregate(reviews)
    async with SessionLocal() as db:
        db.add(CouncilVerdict(session_id=sid, round=0, **agg))
        await db.commit()
    await emit(sid, "council", "done",
               f"Council verdict: {agg['overall'].upper()}; weak blocks: {', '.join(agg['blocks_to_revise']) or 'none'}",
               target="council", detail=agg)
    return agg


# ---------------------------------------------------------------- Phase 4
async def _phase_advisor(sid: str, agg: dict[str, Any]) -> None:
    await _set_phase(sid, "advisor")
    ctx = await _context(sid)
    async with SessionLocal() as db:
        reviews = (await db.execute(select(CouncilReview).where(CouncilReview.session_id == sid))).scalars().all()
    ctx["council"] = {"aggregate": agg, "reviews": [{"seat": r.seat, "verdict": r.verdict, "risks": r.risks,
                                                     "must_verify": r.must_verify, "improve": r.improve} for r in reviews]}
    today = datetime.now(ZoneInfo(settings.timezone))
    ctx["today_malaysia"] = today.strftime("%A %Y-%m-%d %H:%M")
    ctx["knowledge_contacts"] = await kb_search("contact office programme advisory Sarawak Malaysia", k=4)
    out = await run_agent(factories.advisor(sid), json.dumps(ctx, ensure_ascii=False, default=str),
                          ActionsOut, sid, "advisor")
    async with SessionLocal() as db:
        for i, a in enumerate(out.actions[:5]):
            payload = a.model_dump(exclude={"kind", "title", "rationale", "source_agent"})
            if a.kind == "calendar_event":
                payload["start_iso"] = _safe_start(a.start_iso, today, i)
            db.add(ActionItem(session_id=sid, kind=a.kind, title=a.title[:200], rationale=a.rationale,
                              payload=payload, source_agent=a.source_agent[:60]))
        await db.commit()
    await emit(sid, "advisor", "done", f"{len(out.actions[:5])} actions proposed; waiting for your approval (G2)",
               target="advisor", detail={"next_30_days": out.next_30_days})


def _safe_start(iso: str | None, today: datetime, i: int) -> str:
    """Guard the model's date: must be within the next 7 days, 08:00-23:00 MYT; else a default slot."""
    tz = ZoneInfo(settings.timezone)
    try:
        d = datetime.fromisoformat((iso or "").replace("Z", "+00:00")).astimezone(tz)
        if today < d < today + timedelta(days=8) and 8 <= d.hour <= 23:
            return d.isoformat()
    except ValueError:
        pass
    d = (today + timedelta(days=1 + i)).replace(hour=10, minute=0, second=0, microsecond=0)
    return d.isoformat()


async def _report_task(sid: str) -> str:
    from app.routers.sessions import build_report_markdown
    md = await build_report_markdown(sid)
    return await queue.enqueue(sid, "report_builder", {"session_summary_markdown": md[:30000],
                                                       "format": "DOCX (and PDF if available)"}, deadline_s=600)


# ---------------------------------------------------------------- run
async def _run(sid: str) -> None:
    try:
        async with SessionLocal() as db:
            s = await db.get(StartupSession, sid)
        if s.phase in ("intake", "problem"):
            await _phase_problem(s)
            await _wait_gate(sid, "gate_g1")
        await _phase_bmc(sid)
        agg = await _phase_council(sid)
        await _set_phase(sid, "deliverables")
        report_task = await _report_task(sid)
        await _phase_advisor(sid, agg)
        await _wait_gate(sid, "gate_g2")
        await _set_phase(sid, "actions")
        async with SessionLocal() as db:
            approved = (await db.execute(select(ActionItem).where(ActionItem.session_id == sid,
                                                                  ActionItem.approval == "approved"))).scalars().all()
        for a in approved:
            res = await gws.execute(a.id)
            await emit(sid, "advisor", "tool_result", f"{a.kind}: {a.title} → {res.get('status') or res.get('error')}",
                       target="advisor", detail=res)
        report = await queue.wait_for(report_task, timeout_s=300)
        if report is None:
            await emit(sid, "pipeline", "fallback", "WorkBuddy report not ready; the web report is available",
                       target="workbuddy")
        await _set_phase(sid, "done")
    except Exception as e:
        log.exception("pipeline failed")
        await _set_phase(sid, "failed", error=f"{type(e).__name__}: {str(e)[:500]}")
