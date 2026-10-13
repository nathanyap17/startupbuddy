"""REST + SSE for the web app (docs/PROJECT_SPEC.md §9)."""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.agent import pipeline
from app.db import SessionLocal
from app.events import subscribe, unsubscribe
from app.models import (BMC_KEYS, ActionItem, AgentEvent, Artifact, BmcBlock, CouncilReview, CouncilVerdict,
                        DemoUser, EvidenceItem, ProblemStatement, StartupSession, WorkbuddyTask)
from app.workbuddy import queue

router = APIRouter()


class CreateSession(BaseModel):
    intent: str = Field(min_length=5, max_length=500)
    location_text: str = Field(min_length=2, max_length=200)
    auto_g1: bool = False
    auto_g2: bool = False


class GateDecision(BaseModel):
    decision: Literal["approve", "edit", "reject", "clarify"]
    notes: str | None = None
    statement: str | None = None
    action_ids: list[str] = Field(default_factory=list)
    always: bool = False  # "Always allow": auto-approve this checkpoint in future for this session


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class RefineIn(BaseModel):
    instruction: str = Field(min_length=3, max_length=1000)


class SettingsIn(BaseModel):
    auto_g1: bool | None = None
    auto_g2: bool | None = None


def _iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


def _summary(s: StartupSession) -> dict[str, Any]:
    return {"id": s.id, "title": s.title, "intent": s.intent, "location_text": s.location_text,
            "phase": s.phase, "origin": s.origin, "error": s.error, "auto_g1": s.auto_g1, "auto_g2": s.auto_g2,
            "summary": s.summary, "screen": s.screen, "clarification": s.clarification,
            "created_at": _iso(s.created_at), "updated_at": _iso(s.updated_at)}


async def create_session(intent: str, location_text: str, origin: str, auto_g1: bool = False,
                         auto_g2: bool = False) -> dict[str, Any]:
    async with SessionLocal() as db:
        user = (await db.execute(select(DemoUser).limit(1))).scalar_one()
        title = intent if len(intent) <= 60 else intent[:57] + "…"
        s = StartupSession(user_id=user.id, title=title, intent=intent, location_text=location_text, origin=origin,
                           auto_g1=auto_g1, auto_g2=auto_g2)
        db.add(s)
        await db.commit()
        out = _summary(s)
    pipeline.start(out["id"])
    return out


@router.get("/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    async with SessionLocal() as db:
        rows = (await db.execute(select(StartupSession).order_by(StartupSession.created_at.desc()))).scalars().all()
        return [_summary(s) for s in rows]


@router.post("/sessions")
async def post_session(body: CreateSession) -> dict[str, Any]:
    return await create_session(body.intent.strip(), body.location_text.strip(), "web", body.auto_g1, body.auto_g2)


async def session_detail(sid: str) -> dict[str, Any]:
    async with SessionLocal() as db:
        s = await db.get(StartupSession, sid)
        if not s:
            raise HTTPException(404, "session not found")
        p = (await db.execute(select(ProblemStatement).where(ProblemStatement.session_id == sid)
                              .order_by(ProblemStatement.version.desc()).limit(1))).scalar_one_or_none()
        blocks = (await db.execute(select(BmcBlock).where(BmcBlock.session_id == sid))).scalars().all()
        ev = (await db.execute(select(EvidenceItem).where(EvidenceItem.session_id == sid)
                               .order_by(EvidenceItem.created_at))).scalars().all()
        reviews = (await db.execute(select(CouncilReview).where(CouncilReview.session_id == sid)
                                    .order_by(CouncilReview.round))).scalars().all()
        verdicts = (await db.execute(select(CouncilVerdict).where(CouncilVerdict.session_id == sid)
                                     .order_by(CouncilVerdict.round.desc()).limit(2))).scalars().all()
        actions = (await db.execute(select(ActionItem).where(ActionItem.session_id == sid)
                                    .order_by(ActionItem.created_at))).scalars().all()
        arts = (await db.execute(select(Artifact).where(Artifact.session_id == sid)
                                 .order_by(Artifact.created_at.desc()))).scalars().all()  # newest report first
        tasks = (await db.execute(select(WorkbuddyTask).where(WorkbuddyTask.session_id == sid)
                                  .order_by(WorkbuddyTask.created_at))).scalars().all()
    from app.agent import refine
    latest: dict[str, Any] = {}
    history: dict[str, list[dict[str, Any]]] = {}
    for b in sorted(blocks, key=lambda b: b.round):
        latest[b.key] = {"key": b.key, "round": b.round, "version": b.round + 1, "status": b.status, "content": b.content,
                         "instruction": b.instruction, "change_note": b.change_note, "stale_reason": b.stale_reason,
                         "updated_at": _iso(b.updated_at)}
        if b.status == "done":
            history.setdefault(b.key, []).append({"version": b.round + 1, "instruction": b.instruction,
                                                  "change_note": b.change_note, "updated_at": _iso(b.updated_at)})
    for k, v in latest.items():
        v["history"] = history.get(k, [])
    seats = {r.seat: r for r in reviews}  # latest round per seat
    verdict, prev_verdict = (list(verdicts) + [None, None])[:2]
    changed_at = {k: v["updated_at"] for k, v in latest.items() if v["version"] > 1}
    return {
        **_summary(s),
        "lat": s.lat, "lng": s.lng,
        "problem": p and {"statement": p.statement, "target_user": p.target_user, "pain": p.pain,
                          "why_now": p.why_now, "details": p.details, "confirmed_at": _iso(p.confirmed_at)},
        "blocks": [latest.get(k, {"key": k, "status": "pending", "content": {}}) for k in BMC_KEYS],
        "evidence": [{"scope": e.scope, "claim": e.claim, "value": e.value, "label": e.label,
                      "source_url": e.source_url, "method": e.method, "produced_by": e.produced_by} for e in ev],
        "council": [{"seat": r.seat, "round": r.round, "scores": r.scores, "strengths": r.strengths, "risks": r.risks,
                     "must_verify": r.must_verify, "improve": r.improve, "verdict": r.verdict} for r in seats.values()],
        "verdict": verdict and {"block_means": verdict.block_means, "blocks_to_revise": verdict.blocks_to_revise,
                                "overall": verdict.overall, "round": verdict.round, "trigger": verdict.trigger,
                                "previous": prev_verdict and {"block_means": prev_verdict.block_means,
                                                              "overall": prev_verdict.overall}},
        "refining": refine.status(sid),
        "refinable": s.phase in refine.PRE_G2 + refine.POST_G2,
        "actions": [{"id": a.id, "kind": a.kind, "title": a.title, "rationale": a.rationale, "payload": a.payload,
                     "source_agent": a.source_agent, "approval": a.approval, "external_ref": a.external_ref,
                     "external_url": a.external_url, "follow_up": a.follow_up, "follow_up_note": a.follow_up_note,
                     # the block this action came from was refined after the action was proposed
                     "outdated": bool(changed_at.get(a.source_agent) and changed_at[a.source_agent] > _iso(a.created_at))}
                    for a in actions],
        "artifacts": [{"id": a.id, "kind": a.kind, "filename": a.filename, "url": a.url, "size_bytes": a.size_bytes}
                      for a in arts],
        "workbuddy_tasks": [{"id": t.id, "skill": t.skill, "status": t.status, "attempts": t.attempts,
                             "result": t.result} for t in tasks],
        "workbuddy_online": await queue.worker_online(),
    }


@router.get("/sessions/{sid}")
async def get_session(sid: str) -> dict[str, Any]:
    return await session_detail(sid)


@router.delete("/sessions/{sid}")
async def delete_session(sid: str) -> dict[str, bool]:
    async with SessionLocal() as db:
        await db.execute(delete(StartupSession).where(StartupSession.id == sid))
        await db.commit()
    return {"ok": True}


async def decide_gate(sid: str, gate: str, body: GateDecision) -> dict[str, Any]:
    expected = {"G0": "gate_g0", "G1": "gate_g1", "G2": "gate_g2"}.get(gate.upper())
    if not expected:
        raise HTTPException(400, "gate must be G0, G1 or G2")
    async with SessionLocal() as db:
        s = await db.get(StartupSession, sid)
        if not s:
            raise HTTPException(404, "session not found")
        if s.phase != expected:
            raise HTTPException(409, f"session is in phase {s.phase}, not {expected}")
        from app.agent import refine
        if expected == "gate_g2" and refine.status(sid):
            raise HTTPException(409, "a block refinement is still running; approve the actions once it finishes")
        now = datetime.now(timezone.utc)
        if expected == "gate_g0":
            answer = (body.notes or body.statement or "").strip()
            if body.decision == "reject":
                s.phase, s.error = "blocked", "Stopped by the founder at the clarification step"
            else:
                if not answer:
                    raise HTTPException(422, "please answer the clarifying question")
                s.clarification = (s.clarification + "\n" + answer if s.clarification else answer)[:2000]
                s.phase = "screening"
            await db.commit()
            from app.events import emit
            await emit(sid, "founder", "chat", answer if body.decision != "reject" else "Stop here, please.",
                       detail={"role": "user", "channel": "web", "gate": "G0"})
            pipeline.gate_event(sid).set()
            return {"ok": True, "phase": s.phase}
        if body.always:
            if expected == "gate_g1":
                s.auto_g1 = True
            else:
                s.auto_g2 = True
        if expected == "gate_g1":
            p = (await db.execute(select(ProblemStatement).where(ProblemStatement.session_id == sid)
                                  .order_by(ProblemStatement.version.desc()).limit(1))).scalar_one()
            if body.decision == "reject":
                s.phase = "failed"
                s.error = "Founder rejected the problem statement" + (f": {body.notes}" if body.notes else "")
            else:
                if body.decision == "edit" and body.statement:
                    p = ProblemStatement(session_id=sid, version=p.version + 1, statement=body.statement,
                                         target_user=p.target_user, pain=p.pain, why_now=p.why_now, details=p.details)
                    db.add(p)
                p.confirmed_at = now
                s.phase = "bmc"
        else:
            actions = (await db.execute(select(ActionItem).where(ActionItem.session_id == sid))).scalars().all()
            chosen = set(body.action_ids) if body.decision == "approve" else set()
            for a in actions:
                if a.approval == "pending":
                    a.approval = "approved" if a.id in chosen else "rejected"
                    a.decided_at = now
            s.phase = "actions"
        await db.commit()
    pipeline.gate_event(sid).set()
    if s.phase == "failed":
        pipeline.gate_event(sid).set()
    return {"ok": True, "phase": s.phase}


@router.post("/sessions/{sid}/gates/{gate}")
async def post_gate(sid: str, gate: str, body: GateDecision) -> dict[str, Any]:
    return await decide_gate(sid, gate, body)


@router.post("/sessions/{sid}/chat")
async def post_chat(sid: str, body: ChatIn) -> dict[str, Any]:
    from app.agent import refine
    from app.agent.assistant import ask
    async with SessionLocal() as db:
        if not await db.get(StartupSession, sid):
            raise HTTPException(404, "session not found")
    mention = refine.parse_mention(body.message)
    if mention:  # "@Block preference" is a refinement request, not a question
        return await refine_or_explain(sid, mention[0], mention[1], "web")
    return await ask(sid, body.message, "web")


async def refine_or_explain(sid: str, key: str, instruction: str, channel: str) -> dict[str, Any]:
    """Start a refinement; if it can't start, say why in the chat (and return it) instead of failing silently."""
    from app.agent import refine
    from app.events import emit
    try:
        out = await refine.request(sid, key, instruction, channel)
        return {"reply": f"On it: refining {refine.NAME[key]}. {out['message']}.", **out}
    except refine.RefineError as e:
        await emit(sid, "session_assistant", "chat", f"🙏 {e.message}", detail={"role": "assistant", "channel": channel})
        return {"ok": False, "reply": e.message, "status": e.status}


@router.post("/sessions/{sid}/blocks/{key}/refine")
async def post_refine(sid: str, key: str, body: RefineIn) -> dict[str, Any]:
    """Founder's preference for one BMC block: the block agent rewrites it, then the council re-assesses.
    Before G2 only that block is re-scored; after G2 the full council reviews again."""
    from app.agent import refine
    try:
        return await refine.request(sid, key, body.instruction, "web")
    except refine.RefineError as e:
        raise HTTPException(e.status, e.message)


@router.post("/sessions/{sid}/settings")
async def post_settings(sid: str, body: SettingsIn) -> dict[str, Any]:
    """Toggle "Always allow" per checkpoint. Enabling it while that checkpoint is waiting approves it now."""
    async with SessionLocal() as db:
        s = await db.get(StartupSession, sid)
        if not s:
            raise HTTPException(404, "session not found")
        if body.auto_g1 is not None:
            s.auto_g1 = body.auto_g1
        if body.auto_g2 is not None:
            s.auto_g2 = body.auto_g2
        await db.commit()
        phase, a1, a2 = s.phase, s.auto_g1, s.auto_g2
    if (phase == "gate_g1" and a1) or (phase == "gate_g2" and a2):
        await pipeline.auto_approve(sid, phase)
    return {"auto_g1": a1, "auto_g2": a2}


@router.get("/sessions/{sid}/events")
async def stream_events(sid: str, request: Request) -> StreamingResponse:
    last = int(request.headers.get("last-event-id") or request.query_params.get("after") or 0)

    async def gen():
        nonlocal last
        ev = subscribe(sid)
        try:
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                async with SessionLocal() as db:
                    rows = (await db.execute(select(AgentEvent).where(AgentEvent.session_id == sid, AgentEvent.seq > last)
                                             .order_by(AgentEvent.seq).limit(200))).scalars().all()
                for r in rows:
                    last = r.seq
                    data = {"seq": r.seq, "ts": r.ts.isoformat(), "agent": r.agent, "kind": r.kind, "target": r.target,
                            "summary": r.summary, "detail": r.detail, "latency_ms": r.latency_ms}
                    yield f"id: {r.seq}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
                ev.clear()
                try:
                    await asyncio.wait_for(ev.wait(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            unsubscribe(sid, ev)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def build_report_markdown(sid: str) -> str:
    d = await session_detail(sid)
    L = [f"# StartupBuddy report: {d['title']}", "", f"**Intent:** {d['intent']}  ", f"**Location:** {d['location_text']}", ""]
    if d["problem"]:
        p = d["problem"]
        L += ["## 1. Problem statement", p["statement"], "", f"- **Target user:** {p['target_user']}",
              f"- **Pain:** {p['pain']}", f"- **Why now:** {p['why_now']}", ""]
        comps = (p.get("details") or {}).get("competitors") or []
        if comps:
            L += ["**Nearby competitors (Google Maps, within ~1 km):**", "", "| Name | Rating | Reviews | Distance |", "|---|---|---|---|"]
            L += [f"| {c['name']} | {c.get('rating') or '-'} | {c.get('reviews') or '-'} | {c['distance_km']} km |" for c in comps[:8]]
            L.append("")
    L += ["## 2. Business Model Canvas", ""]
    for b in d["blocks"]:
        c = b.get("content") or {}
        L += [f"### {b['key'].replace('_', ' ').title()}", c.get("summary", "(pending)")]
        L += [f"- {i}" for i in c.get("items", [])]
        if c.get("assumptions"):
            L += ["", "*Assumptions to test:* " + "; ".join(c["assumptions"])]
        L.append("")
    refined = [b for b in d["blocks"] if (b.get("version") or 1) > 1]
    if refined:
        L += ["### Founder refinements", ""]
        L += [f"- **{b['key'].replace('_', ' ').title()} v{h['version']}**: \u201c{h['instruction']}\u201d: {h['change_note']}"
              for b in refined for h in b.get("history", []) if h.get("instruction")]
        L.append("")
    stale = [b for b in d["blocks"] if b.get("stale_reason")]
    if stale:
        L += ["*Blocks to re-check after a change:* " + "; ".join(
            f"{b['key'].replace('_', ' ').title()} ({b['stale_reason']})" for b in stale), ""]
    if d["verdict"]:
        v = d["verdict"]
        L += ["## 3. Council review", f"**Overall verdict:** {v['overall'].upper()} (review round {v['round'] + 1}"
              + (f", after: {v['trigger']}" if v.get("trigger") and v["round"] else "") + ")  ",
              f"**Blocks to revise:** {', '.join(v['blocks_to_revise']) or 'none'}", ""]
        for r in d["council"]:
            L += [f"### {r['seat'].upper()}: {r['verdict']}"]
            L += [f"- Risk: {x}" for x in r["risks"][:3]] + [f"- Improve: {x}" for x in r["improve"][:3]]
            L.append("")
        L += ["## 4. Measure / Improve / Verify", "", "**Must verify:**"]
        L += [f"- {x}" for r in d["council"] for x in r["must_verify"][:2]]
        L.append("")
    if d["actions"]:
        L += ["## 5. First actions", ""]
        L += [f"- [{a['approval']}] {a['title']} ({a['kind']}, from {a['source_agent']})" for a in d["actions"]]
        L.append("")
    L += ["## Evidence appendix", "", "| Claim | Value | Label | Source / method |", "|---|---|---|---|"]
    for e in d["evidence"]:
        src = e["source_url"] or e["method"] or ""
        L.append(f"| {e['claim']} | {e['value'] or ''} | {e['label']} | {src} |")
    return "\n".join(L)


@router.get("/sessions/{sid}/report", response_class=PlainTextResponse)
async def get_report(sid: str) -> str:
    return await build_report_markdown(sid)


@router.post("/sessions/{sid}/report/docx")
async def rerender_docx(sid: str) -> dict[str, Any]:
    """(Re)build the DOCX from the latest WorkBuddy report_builder result."""
    from app.workbuddy.queue import _store_report_docx
    async with SessionLocal() as db:
        t = (await db.execute(select(WorkbuddyTask).where(WorkbuddyTask.session_id == sid, WorkbuddyTask.skill == "report_builder",
                                                          WorkbuddyTask.status == "succeeded")
                              .order_by(WorkbuddyTask.finished_at.desc()).limit(1))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "no WorkBuddy report for this session yet")
    await _store_report_docx(sid, t.id, t.result or {})
    return {"ok": True}


class FollowUpIn(BaseModel):
    status: Literal["done", "reschedule", "cancelled"]
    note: str | None = None


@router.post("/sessions/{sid}/followups/check")
async def check_followups(sid: str) -> dict[str, Any]:
    from app.agent import followup
    return {"results": await followup.check(sid)}


@router.post("/sessions/{sid}/actions/{aid}/followup")
async def update_followup(sid: str, aid: str, body: FollowUpIn) -> dict[str, Any]:
    """Founder's update after a site visit or meeting ('waiting for your update')."""
    from app.events import emit
    async with SessionLocal() as db:
        a = await db.get(ActionItem, aid)
        if not a or a.session_id != sid:
            raise HTTPException(404, "action not found")
        a.follow_up, a.follow_up_note = body.status, (body.note or a.follow_up_note)
        a.follow_up_at = datetime.now(timezone.utc)
        await db.commit()
        title = a.title
    say = {"done": f"🙌 Nice! “{title}” is done", "reschedule": f"🔁 Noted, “{title}” needs a new time",
           "cancelled": f"🗑️ “{title}” cancelled"}[body.status]
    await emit(sid, "founder", "followup", say + (f": {body.note}" if body.note else ""), target="advisor")
    return {"ok": True}


@router.post("/sessions/{sid}/actions/{aid}/retry")
async def retry_action(sid: str, aid: str) -> dict[str, Any]:
    """Re-run an action the founder already approved whose execution failed (e.g. Google not linked yet).
    Rule 1 holds: only actions that were approved at G2 can be retried."""
    from app.mcp import gws
    async with SessionLocal() as db:
        a = await db.get(ActionItem, aid)
        if not a or a.session_id != sid:
            raise HTTPException(404, "action not found")
        if a.approval != "exec_failed" or a.decided_at is None:
            raise HTTPException(409, f"only approved actions that failed can be retried (state: {a.approval})")
        a.approval = "approved"
        await db.commit()
    res = await gws.execute(aid)
    from app.events import emit
    await emit(sid, "advisor", "tool_result", f"retry {aid[-6:]} → {res.get('status') or res.get('error')}", target="advisor", detail=res)
    return res


@router.get("/artifacts/{aid}")
async def get_artifact(aid: str) -> Response:
    async with SessionLocal() as db:
        a = await db.get(Artifact, aid)
        if not a or a.data is None:
            raise HTTPException(404, "artifact not found")
        return Response(a.data, media_type=a.content_type or "application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{a.filename}"'})
