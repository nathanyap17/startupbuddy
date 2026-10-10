"""Google Workspace actions for the Advisor (reuses the PepperDex calendar pattern).

Rule 1: every function takes an action_id and refuses unless that action is approved in the DB.
Emails are DRAFTS only. Token: OAuth user token (demo account) from GWS_TOKEN_FILE."""
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
SCOPES = ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/gmail.compose"]


def _token_path() -> Path:
    p = Path(settings.gws_token_file)
    return p if p.is_absolute() else BACKEND_DIR / p


def available() -> bool:
    return _token_path().exists()


def _creds() -> Credentials:
    creds = Credentials.from_authorized_user_file(str(_token_path()), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _calendar_insert(a: ActionItem) -> tuple[str, str]:
    p = a.payload
    start = dt.datetime.fromisoformat((p.get("start_iso") or "").replace("Z", "+00:00"))
    end = start + dt.timedelta(minutes=int(p.get("duration_min") or 45))
    body = {
        "summary": a.title,
        "description": f"{a.rationale}\n\nProposed by StartupBuddy ({a.source_agent}), approved by the founder.",
        "location": p.get("location", ""),
        "start": {"dateTime": start.isoformat(), "timeZone": settings.timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": settings.timezone},
        "conferenceData": {"createRequest": {"requestId": a.id, "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
    }
    svc = build("calendar", "v3", credentials=_creds(), cache_discovery=False)
    ev = svc.events().insert(calendarId="primary", body=body, conferenceDataVersion=1).execute()
    return ev["id"], ev.get("htmlLink", "")


def _gmail_draft(a: ActionItem) -> tuple[str, str]:
    p = a.payload
    msg = EmailMessage()
    if p.get("email_to"):
        msg["To"] = p["email_to"]
    msg["Subject"] = p.get("email_subject") or a.title
    msg.set_content(p.get("email_body") or a.rationale)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc = build("gmail", "v1", credentials=_creds(), cache_discovery=False)
    d = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return d["id"], "https://mail.google.com/mail/u/0/#drafts"


async def execute(action_id: str) -> dict:
    async with SessionLocal() as db:
        a = await db.get(ActionItem, action_id)
        if not a:
            return {"error": "unknown_action"}
        if a.approval != "approved":
            return {"error": "action_not_approved", "action_id": action_id}
        if not available():
            a.approval = "exec_failed"
            a.external_ref = "Google account not linked (token missing)"
            await db.commit()
            return {"error": "gws_not_linked"}
        try:
            fn = _calendar_insert if a.kind == "calendar_event" else _gmail_draft
            ref, url = await asyncio.to_thread(fn, a)
            a.approval, a.external_ref, a.external_url = "executed", ref, url
            a.executed_at = dt.datetime.now(dt.timezone.utc)
        except Exception as e:
            log.exception("gws action failed")
            a.approval, a.external_ref = "exec_failed", f"{type(e).__name__}: {str(e)[:300]}"
        await db.commit()
        return {"status": a.approval, "ref": a.external_ref, "url": a.external_url}
