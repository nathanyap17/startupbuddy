"""Follow-up watcher: after an approved email_outreach draft is SENT by the founder, watch its Gmail thread
for a reply. If the reply proposes a time, put the meeting in the founder's own calendar (Meet link only if the
reply says online; no attendees, so nobody is invited). Otherwise summarise the reply and suggest a next step.

Consent: this is the follow-up plan the founder approved at G2 ("wait for reply, then schedule")."""
import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from sqlalchemy import select

from app.agent import prompts
from app.agent.common import make_agent, run_agent
from app.config import settings
from app.db import SessionLocal
from app.events import emit
from app.mcp import gws
from app.models import ActionItem
from app.schemas.agents import FollowUpOut

log = logging.getLogger("startupbuddy.followup")
_warned_scope: set[str] = set()


def _header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _body_text(msg: dict) -> str:
    def walk(part: dict) -> str:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"] + "==").decode("utf-8", "replace")
        for p in part.get("parts", []) or []:
            t = walk(p)
            if t:
                return t
        return ""
    return (walk(msg.get("payload", {})) or msg.get("snippet", ""))[:4000]


def _read_thread(thread_id: str) -> dict:
    """Return {'state': 'draft'|'sent'|'replied', 'reply': {...}} for a Gmail thread."""
    c = gws.creds()
    svc = build("gmail", "v1", credentials=c, cache_discovery=False)
    me = svc.users().getProfile(userId="me").execute().get("emailAddress", "").lower()
    th = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
    msgs = th.get("messages", [])
    if all("DRAFT" in (m.get("labelIds") or []) for m in msgs):
        return {"state": "draft"}
    replies = [m for m in msgs if "DRAFT" not in (m.get("labelIds") or []) and me not in _header(m, "From").lower()]
    if not replies:
        return {"state": "sent"}
    r = replies[-1]
    return {"state": "replied", "reply": {"from": _header(r, "From"), "subject": _header(r, "Subject"),
                                          "date": _header(r, "Date"), "text": _body_text(r)}}


async def _handle_reply(a: ActionItem, reply: dict) -> str:
    today = datetime.now(ZoneInfo(settings.timezone)).strftime("%A %Y-%m-%d %H:%M")
    agent = make_agent("follow_up", prompts.FOLLOW_UP, FollowUpOut, a.session_id, "advisor")
    out = await run_agent(agent, json.dumps({"today_malaysia": today, "original_action": a.title, "reply": reply},
                                            ensure_ascii=False), FollowUpOut, a.session_id, "advisor", timeout_s=60)
    sender = reply.get("from", "They").split("<")[0].strip() or "They"
    if out.proposes_time and out.start_iso:
        title = f"Meeting: {a.title}"
        desc = f"Scheduled from their reply: {out.reply_summary}\nNext: {out.suggested_next_step}"
        ref, url = await asyncio.to_thread(gws.insert_event, title, desc, out.start_iso, out.duration_min,
                                           out.location, out.is_online, f"fu-{a.id}")
        when = datetime.fromisoformat(out.start_iso.replace("Z", "+00:00")).astimezone(ZoneInfo(settings.timezone))
        note = f"{out.reply_summary} → booked {when:%a %d %b, %I:%M %p}" + (" (Google Meet)" if out.is_online else f" at {out.location or 'the place they named'}")
        state, say = "scheduled", f"📬 {sender} replied! I put it in your calendar for {when:%a %d %b, %I:%M %p}" + (" with a Meet link 💻" if out.is_online else " 📍")
        extra = {"event_url": url, "event_id": ref}
    else:
        note = f"{out.reply_summary} · Next: {out.suggested_next_step}"
        state, say, extra = "replied", f"📬 {sender} replied: {out.reply_summary} Next step: {out.suggested_next_step}", {}
    async with SessionLocal() as db:
        row = await db.get(ActionItem, a.id)
        row.follow_up, row.follow_up_note, row.follow_up_at = state, note[:1000], datetime.now(timezone.utc)
        await db.commit()
    await emit(a.session_id, "advisor", "followup", say, target="advisor", detail={"action_id": a.id, **extra})
    return state


async def check(session_id: str | None = None) -> list[dict]:
    """Check every approved email_outreach waiting for a reply (optionally for one session)."""
    if not gws.available():
        return []
    q = select(ActionItem).where(ActionItem.follow_up == "waiting_reply", ActionItem.thread_id.is_not(None))
    if session_id:
        q = q.where(ActionItem.session_id == session_id)
    async with SessionLocal() as db:
        items = (await db.execute(q)).scalars().all()
    if not items:
        return []
    if not gws.can_read_mail():
        for a in items:
            if a.session_id not in _warned_scope:
                _warned_scope.add(a.session_id)
                await emit(a.session_id, "advisor", "fallback",
                           "🔌 To watch for email replies, reconnect Google once (read-only Gmail permission is missing)",
                           target="advisor")
        return [{"action_id": a.id, "state": "needs_reconnect"} for a in items]
    results = []
    for a in items:
        try:
            r = await asyncio.to_thread(_read_thread, a.thread_id)
            state = r["state"]
            if state == "replied":
                state = await _handle_reply(a, r["reply"])
            results.append({"action_id": a.id, "state": state})
        except Exception as e:
            log.warning("follow-up check failed for %s: %s", a.id, e)
            results.append({"action_id": a.id, "state": "error", "error": type(e).__name__})
    return results


async def watcher(interval_s: int = 120) -> None:
    """Background loop (single Cloud Run instance, CPU always on)."""
    while True:
        try:
            await check()
        except Exception:
            log.exception("follow-up watcher iteration failed")
        await asyncio.sleep(interval_s)
