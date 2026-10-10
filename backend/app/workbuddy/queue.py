"""WorkBuddy task queue (docs/MCP_CONTRACT.md). Agents enqueue; WorkBuddy claims via MCP
long-poll; results wake the waiting agent. Bounded by lease, deadline and attempts (rule 4)."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, update

from app.config import settings
from app.db import SessionLocal
from app.events import emit
from app.models import Artifact, WorkbuddyTask, WorkerHeartbeat
from app.workbuddy.schemas import SKILL_SCHEMAS

LEASE_S = 180
MAX_ATTEMPTS = 2
MAX_WAIT_S = 25
_new_task = asyncio.Event()
_done: dict[str, asyncio.Event] = {}


def now() -> datetime:
    return datetime.now(timezone.utc)


async def enqueue(session_id: str, skill: str, inputs: dict[str, Any], deadline_s: int | None = None) -> str:
    schema = SKILL_SCHEMAS[skill].model_json_schema()
    async with SessionLocal() as db:
        t = WorkbuddyTask(session_id=session_id, skill=skill, inputs=inputs, output_schema=schema,
                          deadline_at=now() + timedelta(seconds=deadline_s or settings.workbuddy_task_deadline_s))
        db.add(t)
        await db.commit()
        task_id = t.id
    _done[task_id] = asyncio.Event()
    _new_task.set()
    await emit(session_id, "workbuddy", "handoff", f"Queued WorkBuddy task: {skill}", target="workbuddy",
               detail={"task_id": task_id, "skill": skill})
    return task_id


async def _requeue_and_expire() -> None:
    async with SessionLocal() as db:
        await db.execute(update(WorkbuddyTask)
                         .where(WorkbuddyTask.status == "claimed", WorkbuddyTask.lease_until < now(),
                                WorkbuddyTask.attempts < MAX_ATTEMPTS)
                         .values(status="queued", worker_id=None))
        expired = (await db.execute(select(WorkbuddyTask).where(
            WorkbuddyTask.status.in_(("queued", "claimed")), WorkbuddyTask.deadline_at < now()))).scalars().all()
        for t in expired:
            t.status, t.finished_at, t.error = "expired", now(), "deadline passed"
        await db.commit()
    for t in expired:
        if t.id in _done:
            _done[t.id].set()


async def _try_claim(worker_id: str) -> dict[str, Any] | None:
    async with SessionLocal() as db:
        t = (await db.execute(select(WorkbuddyTask).where(WorkbuddyTask.status == "queued")
                              .order_by(WorkbuddyTask.created_at).limit(1)
                              .with_for_update(skip_locked=True))).scalar_one_or_none()
        if not t:
            return None
        t.status, t.worker_id, t.claimed_at = "claimed", worker_id, now()
        t.lease_until, t.attempts = now() + timedelta(seconds=LEASE_S), t.attempts + 1
        await db.commit()
        payload = {"task_id": t.id, "skill": t.skill, "session_id": t.session_id, "inputs": t.inputs,
                   "output_schema": t.output_schema, "deadline_at": t.deadline_at.isoformat(),
                   "instructions": f"Follow the WorkBuddy skill 'startupbuddy-{t.skill.replace('_', '-')}'. "
                                   "Return JSON matching output_schema via submit_task_result."}
        session_id = t.session_id
    await emit(session_id, "workbuddy", "start", f"WorkBuddy picked up {payload['skill']}", target="workbuddy",
               detail={"task_id": payload["task_id"], "worker_id": worker_id})
    return payload


async def heartbeat(worker_id: str) -> None:
    async with SessionLocal() as db:
        hb = await db.get(WorkerHeartbeat, worker_id)
        if hb:
            hb.last_seen = now()
        else:
            db.add(WorkerHeartbeat(worker_id=worker_id, last_seen=now()))
        await db.commit()


async def worker_online(within_s: int = 90) -> bool:
    async with SessionLocal() as db:
        row = (await db.execute(select(WorkerHeartbeat).where(
            WorkerHeartbeat.last_seen > now() - timedelta(seconds=within_s)).limit(1))).scalar_one_or_none()
        return row is not None


async def claim(worker_id: str, wait_s: int) -> dict[str, Any] | None:
    """Long-poll: return a task or None within wait_s (clamped to 25 s, rule 5)."""
    wait_s = max(1, min(int(wait_s), MAX_WAIT_S))
    await heartbeat(worker_id)
    loop = asyncio.get_running_loop()
    end = loop.time() + wait_s
    while True:
        await _requeue_and_expire()
        task = await _try_claim(worker_id)
        if task:
            return task
        remaining = end - loop.time()
        if remaining <= 0:
            return None
        _new_task.clear()
        try:
            await asyncio.wait_for(_new_task.wait(), timeout=min(remaining, 2.0))
        except TimeoutError:
            pass


async def extend_lease(task_id: str) -> str | None:
    async with SessionLocal() as db:
        t = await db.get(WorkbuddyTask, task_id)
        if not t or t.status != "claimed":
            return None
        t.lease_until = now() + timedelta(seconds=LEASE_S)
        await db.commit()
        return t.lease_until.isoformat()


async def submit(task_id: str, result_json: str) -> dict[str, Any]:
    try:
        raw = json.loads(result_json)
    except json.JSONDecodeError as e:
        return {"ok": False, "validation_errors": [f"result_json is not valid JSON: {e}"]}
    async with SessionLocal() as db:
        t = await db.get(WorkbuddyTask, task_id)
        if not t:
            return {"ok": False, "validation_errors": ["unknown task_id"]}
        if t.status not in ("claimed", "queued"):
            return {"ok": False, "validation_errors": [f"task is already {t.status}"]}
        try:
            parsed = SKILL_SCHEMAS[t.skill].model_validate(raw)
        except ValidationError as e:
            errs = [".".join(str(p) for p in x["loc"]) + ": " + x["msg"] for x in e.errors()]
            return {"ok": False, "validation_errors": errs[:10]}
        t.status, t.result, t.finished_at = "succeeded", parsed.model_dump(), now()
        await db.commit()
        session_id, skill, result = t.session_id, t.skill, t.result
    await emit(session_id, "workbuddy", "done", f"WorkBuddy finished {skill}", target="workbuddy",
               detail={"task_id": task_id})
    if skill == "report_builder":
        await _store_report_docx(session_id, task_id, result)
    if task_id in _done:
        _done[task_id].set()
    return {"ok": True, "validation_errors": []}


async def _store_report_docx(session_id: str, task_id: str, result: dict[str, Any]) -> None:
    """Render WorkBuddy's report_markdown to DOCX and attach it to the session (never fails the submit)."""
    import re

    from app.workbuddy.docx_render import render
    try:
        title = result.get("title") or "StartupBuddy Report"
        data = await asyncio.to_thread(render, result.get("report_markdown") or "", title)
        fname = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")[:80] + ".docx"
        async with SessionLocal() as db:
            a = Artifact(session_id=session_id, task_id=task_id, kind="report", filename=fname, url="",
                         size_bytes=len(data), data=data,
                         content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            db.add(a)
            await db.flush()
            a.url = f"{settings.public_base_url.rstrip('/')}/artifacts/{a.id}"
            await db.commit()
        await emit(session_id, "workbuddy", "done", f"Report DOCX ready ({len(data) // 1024} KB)", target="workbuddy",
                   detail={"artifact": fname})
    except Exception as e:  # rendering is a convenience; the markdown report stays available
        await emit(session_id, "workbuddy", "error", f"DOCX rendering failed: {type(e).__name__}", target="workbuddy")


async def fail(task_id: str, reason: str) -> bool:
    async with SessionLocal() as db:
        t = await db.get(WorkbuddyTask, task_id)
        if not t:
            return False
        t.status, t.error, t.finished_at = "failed", reason[:1000], now()
        await db.commit()
        session_id = t.session_id
    await emit(session_id, "workbuddy", "error", f"WorkBuddy task failed: {reason[:200]}", target="workbuddy")
    if task_id in _done:
        _done[task_id].set()
    return True


async def wait_for(task_id: str, timeout_s: int) -> dict[str, Any] | None:
    """Wait for a result; None on failure/expiry/timeout (caller falls back, rule 4)."""
    ev = _done.setdefault(task_id, asyncio.Event())
    try:
        await asyncio.wait_for(ev.wait(), timeout=timeout_s)
    except TimeoutError:
        pass
    async with SessionLocal() as db:
        t = await db.get(WorkbuddyTask, task_id)
        if t and t.status == "succeeded":
            return t.result
        if t and t.status in ("queued", "claimed"):
            t.status, t.finished_at, t.error = "expired", now(), "agent wait timed out"
            await db.commit()
    return None
