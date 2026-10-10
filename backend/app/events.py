"""agent_event: audit log + live canvas feed. Single Cloud Run instance in the pilot,
so an in-process pub/sub wakes SSE listeners; the DB row is the source of truth."""
import asyncio
import logging
from collections import defaultdict
from typing import Any

from app.db import SessionLocal
from app.models import AgentEvent

log = logging.getLogger("startupbuddy.events")
_listeners: dict[str, set[asyncio.Event]] = defaultdict(set)


async def emit(session_id: str, agent: str, kind: str, summary: str, *, target: str | None = None,
               detail: dict[str, Any] | None = None, latency_ms: int | None = None) -> None:
    async with SessionLocal() as db:
        db.add(AgentEvent(session_id=session_id, agent=agent, kind=kind, target=target,
                          summary=summary[:2000], detail=detail or {}, latency_ms=latency_ms))
        await db.commit()
    log.info("[%s] %s %s %s: %s", session_id[-6:], agent, kind, target or "", summary[:160])
    for ev in list(_listeners.get(session_id, ())):
        ev.set()


def subscribe(session_id: str) -> asyncio.Event:
    ev = asyncio.Event()
    _listeners[session_id].add(ev)
    return ev


def unsubscribe(session_id: str, ev: asyncio.Event) -> None:
    _listeners[session_id].discard(ev)
