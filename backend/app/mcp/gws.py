"""Google Workspace actions for the Advisor (reuses the PepperDex calendar pattern).

Rule 1: every action needs explicit approval in the DB before it runs. Emails are DRAFTS only.
Kinds: email_outreach (Gmail draft, then watch for a reply), site_visit (calendar, no video link),
online_meeting (calendar + Meet), task (checklist only). Legacy kinds calendar_event / gmail_draft still work.
Token: OAuth user token (demo account) from GWS_TOKEN_FILE; its own scopes decide what is possible."""
import asyncio
import base64
import datetime as dt
import logging
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import BACKEND_DIR, settings
from app.db import SessionLocal
from app.models import ActionItem

log = logging.getLogger("startupbuddy.gws")
SCOPES = ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/gmail.compose",
          "https://www.googleapis.com/auth/gmail.readonly"]
READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
EMAIL_KINDS = ("email_outreach", "gmail_draft")
MEET_KINDS = ("online_meeting", "calendar_event")


def _token_path() -> Path:
    p = Path(settings.gws_token_file)
    return p if p.is_absolute() else BACKEND_DIR / p


def available() -> bool:
    return _token_path().exists()


def creds() -> Credentials:
    c = Credentials.from_authorized_user_file(str(_token_path()))  # scopes come from the token itself
    if c.expired and c.refresh_token:
        c.refresh(Request())
    return c


def can_read_mail() -> bool:
    try:
        return available() and creds().has_scopes([READ_SCOPE])
    except Exception:
        return False


def insert_event(title: str, description: str, start_iso: str, duration_min: int, location: str,
                 with_meet: bool, request_id: str) -> tuple[str, str]:
    """Event in the founder's own calendar only: no attendees, so nobody is invited without consent."""
    start = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end = start + dt.timedelta(minutes=int(duration_min or 45))
    body: dict = {
        "summary": title, "description": description, "location": location or "",
        "start": {"dateTime": start.isoformat(), "timeZone": settings.timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": settings.timezone},
    }
    if with_meet:
        body["conferenceData"] = {"createRequest": {"requestId": request_id, "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
    svc = build("calendar", "v3", credentials=creds(), cache_discovery=False)
    ev = svc.events().insert(calendarId="primary", body=body, conferenceDataVersion=1 if with_meet else 0).execute()
    return ev["id"], ev.get("htmlLink", "")


def _calendar(a: ActionItem) -> tuple[str, str]:
    p = a.payload
    desc = f"{a.rationale}\n\nProposed by StartupBuddy ({a.source_agent}), approved by the founder."
    if p.get("follow_up_plan"):
        desc += f"\nNext: {p['follow_up_plan']}"
    return insert_event(a.title, desc, p.get("start_iso") or "", p.get("duration_min") or 45, p.get("location", ""),
                        a.kind in MEET_KINDS, a.id)


def _gmail_draft(a: ActionItem) -> tuple[str, str, str]:
    p = a.payload
    msg = EmailMessage()
    if p.get("email_to"):
        msg["To"] = p["email_to"]
    msg["Subject"] = p.get("email_subject") or a.title
    msg.set_content(p.get("email_body") or a.rationale)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc = build("gmail", "v1", credentials=creds(), cache_discovery=False)
    d = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return d["id"], "https://mail.google.com/mail/u/0/#drafts", d.get("message", {}).get("threadId", "")


async def execute(action_id: str) -> dict:
    async with SessionLocal() as db:
        a = await db.get(ActionItem, action_id)
        if not a:
            return {"error": "unknown_action"}
        if a.approval != "approved":
            return {"error": "action_not_approved", "action_id": action_id}
        now = dt.datetime.now(dt.timezone.utc)
        if a.kind == "task":  # checklist only: nothing leaves the app
            a.approval, a.external_ref, a.follow_up, a.executed_at = "executed", "checklist", "todo", now
            await db.commit()
            return {"status": "executed", "ref": "checklist", "url": None}
        if not available():
            a.approval = "exec_failed"
            a.external_ref = "Google account not linked (token missing)"
            await db.commit()
            return {"error": "gws_not_linked"}
        try:
            if a.kind in EMAIL_KINDS:
                ref, url, thread = await asyncio.to_thread(_gmail_draft, a)
                a.thread_id, a.follow_up = thread or None, "waiting_reply"
            else:
                ref, url = await asyncio.to_thread(_calendar, a)
                a.follow_up = "awaiting_update" if a.kind == "site_visit" else "scheduled"
            a.approval, a.external_ref, a.external_url, a.executed_at = "executed", ref, url, now
        except Exception as e:
            log.exception("gws action failed")
            a.approval, a.external_ref = "exec_failed", f"{type(e).__name__}: {str(e)[:300]}"
        await db.commit()
        return {"status": a.approval, "ref": a.external_ref, "url": a.external_url}
