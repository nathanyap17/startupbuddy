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


class GateDecision(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    notes: str | None = None
    statement: str | None = None
    action_ids: list[str] = Field(default_factory=list)


def _iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


def _summary(s: StartupSession) -> dict[str, Any]:
    return {"id": s.id, "title": s.title, "intent": s.intent, "location_text": s.location_text,
            "phase": s.phase, "origin": s.origin, "error": s.error,
            "created_at": _iso(s.created_at), "updated_at": _iso(s.updated_at)}


async def create_session(intent: str, location_text: str, origin: str) -> dict[str, Any]:
    async with SessionLocal() as db:
        user = (await db.execute(select(DemoUser).limit(1))).scalar_one()
        title = intent if len(intent) <= 60 else intent[:57] + "…"
        s = StartupSession(user_id=user.id, title=title, intent=intent, location_text=location_text, origin=origin)
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
    return await create_session(body.intent.strip(), body.location_text.strip(), "web")


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
        reviews = (await db.execute(select(CouncilReview).where(CouncilReview.session_id == sid))).scalars().all()
        verdict = (await db.execute(select(CouncilVerdict).where(CouncilVerdict.session_id == sid)
                                    .order_by(CouncilVerdict.round.desc()).limit(1))).scalar_one_or_none()
        actions = (await db.execute(select(ActionItem).where(ActionItem.session_id == sid)
                                    .order_by(ActionItem.created_at))).scalars().all()
        arts = (await db.execute(select(Artifact).where(Artifact.session_id == sid))).scalars().all()
        tasks = (await db.execute(select(WorkbuddyTask).where(WorkbuddyTask.session_id == sid)
                                  .order_by(WorkbuddyTask.created_at))).scalars().all()
    latest: dict[str, Any] = {}
    for b in sorted(blocks, key=lambda b: b.round):
        latest[b.key] = {"key": b.key, "round": b.round, "status": b.status, "content": b.content}
    return {
        **_summary(s),
        "lat": s.lat, "lng": s.lng,
        "problem": p and {"statement": p.statement, "target_user": p.target_user, "pain": p.pain,
                          "why_now": p.why_now, "details": p.details, "confirmed_at": _iso(p.confirmed_at)},
        "blocks": [latest.get(k, {"key": k, "status": "pending", "content": {}}) for k in BMC_KEYS],
        "evidence": [{"scope": e.scope, "claim": e.claim, "value": e.value, "label": e.label,
                      "source_url": e.source_url, "method": e.method, "produced_by": e.produced_by} for e in ev],
        "council": [{"seat": r.seat, "scores": r.scores, "strengths": r.strengths, "risks": r.risks,
                     "must_verify": r.must_verify, "improve": r.improve, "verdict": r.verdict} for r in reviews],
        "verdict": verdict and {"block_means": verdict.block_means, "blocks_to_revise": verdict.blocks_to_revise,
                                "overall": verdict.overall},
        "actions": [{"id": a.id, "kind": a.kind, "title": a.title, "rationale": a.rationale, "payload": a.payload,
                     "source_agent": a.source_agent, "approval": a.approval, "external_ref": a.external_ref,
                     "external_url": a.external_url} for a in actions],
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
    expected = {"G1": "gate_g1", "G2": "gate_g2"}.get(gate.upper())
    if not expected:
        raise HTTPException(400, "gate must be G1 or G2")
    async with SessionLocal() as db:
        s = await db.get(StartupSession, sid)
        if not s:
            raise HTTPException(404, "session not found")
        if s.phase != expected:
            raise HTTPException(409, f"session is in phase {s.phase}, not {expected}")
        now = datetime.now(timezone.utc)
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
    if d["verdict"]:
        v = d["verdict"]
        L += ["## 3. Council review", f"**Overall verdict:** {v['overall'].upper()}  ",
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


@router.get("/artifacts/{aid}")
async def get_artifact(aid: str) -> Response:
    async with SessionLocal() as db:
        a = await db.get(Artifact, aid)
        if not a or a.data is None:
            raise HTTPException(404, "artifact not found")
        return Response(a.data, media_type=a.content_type or "application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{a.filename}"'})
