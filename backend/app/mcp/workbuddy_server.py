"""WorkBuddy-facing MCP server (docs/MCP_CONTRACT.md). Mounted at /mcp, X-API-Key required.
Every tool returns within 25 s (rule 5); long work goes through the task queue."""
import base64
import hmac
import logging
import mimetypes

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from app.config import settings
from app.db import SessionLocal
from app.models import Artifact, WorkbuddyTask
from app.workbuddy import queue

log = logging.getLogger("startupbuddy.mcp")
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024

server = MCPServer(
    name="startupbuddy",
    instructions=("StartupBuddy: agentic startup studio for Malaysian founders. Use start_session for a new "
                  "business idea, then run the worker loop: await_next_task → do the task with the named "
                  "startupbuddy skill → submit_task_result. Never approve G2 actions without the user."),
)


def _app_url(sid: str) -> str:
    return f"{settings.frontend_origin.split(',')[0].strip().rstrip('/')}/app/s/{sid}"


@server.tool()
async def start_session(intent: str, location: str) -> dict:
    """Start a StartupBuddy session for a business idea in Malaysia.

    Args:
        intent: The founder's idea in one sentence, e.g. "I want to sell kolo mee".
        location: A Malaysian place, e.g. "Padungan, Kuching".

    Returns: {session_id, app_url}. Share app_url so the user can watch the agents work.
    """
    from app.routers.sessions import create_session
    s = await create_session(intent.strip(), location.strip(), "workbuddy")
    return {"session_id": s["id"], "app_url": _app_url(s["id"])}


@server.tool()
async def get_session_status(session_id: str) -> dict:
    """Current phase of a session and whether a gate (G1 problem, G2 actions) is waiting for the user."""
    from app.routers.sessions import session_detail
    d = await session_detail(session_id)
    gate = {"gate_g1": "G1", "gate_g2": "G2"}.get(d["phase"])
    out = {"phase": d["phase"], "gate_waiting": gate, "app_url": _app_url(session_id), "error": d["error"]}
    if gate == "G1" and d["problem"]:
        out["problem_statement"] = d["problem"]["statement"]
    if gate == "G2":
        out["actions"] = [{"id": a["id"], "kind": a["kind"], "title": a["title"]} for a in d["actions"]
                          if a["approval"] == "pending"]
    return out


@server.tool()
async def confirm_gate(session_id: str, gate: str, decision: str, notes: str = "",
                       action_ids: list[str] | None = None, always: bool = False) -> dict:
    """Pass the USER's decision for a gate. Only call after the user explicitly answered.

    Args:
        session_id: The session.
        gate: "G1" (problem statement) or "G2" (actions).
        decision: "approve" or "reject".
        notes: Optional user notes.
        action_ids: For G2, the exact action ids the user approved (others are rejected).
        always: True only if the user explicitly said "always allow": future checkpoints of this
            kind in this session are then approved automatically (logged in the feed).
    """
    from app.routers.sessions import GateDecision, decide_gate
    return await decide_gate(session_id, gate, GateDecision(decision=decision, notes=notes or None,
                                                            action_ids=action_ids or [], always=always))


@server.tool()
async def ask_session(session_id: str, question: str) -> dict:
    """Ask StartupBuddy a question about a session's plan (problem, canvas, council, evidence, actions).
    Answers are friendly and grounded in that session's data. Takes up to ~20 s."""
    import asyncio
    from app.agent.assistant import ask
    try:
        return await asyncio.wait_for(ask(session_id, question, "workbuddy"), timeout=24)
    except TimeoutError:
        return {"reply": "Still thinking about that one. Please check the web app chat in a moment."}


@server.tool()
async def await_next_task(worker_id: str, wait_s: int = 20) -> dict:
    """Long-poll for the next StartupBuddy task (waits up to wait_s seconds, max 25).

    Returns {"task": null} if nothing is queued (call again), or {"task": {task_id, skill, inputs,
    output_schema, instructions}}. Do the task with the matching startupbuddy skill, then call
    submit_task_result.
    """
    task = await queue.claim(worker_id, wait_s)
    return {"task": task}


@server.tool()
async def heartbeat_task(task_id: str) -> dict:
    """Extend the lease on a task you are still working on (call about every 60 s)."""
    return {"lease_until": await queue.extend_lease(task_id)}


@server.tool()
async def submit_task_result(task_id: str, result_json: str) -> dict:
    """Submit the result for a task. result_json must be a JSON string matching the task's output_schema.

    Returns {ok, validation_errors}. If validation_errors is not empty, fix the JSON and resubmit once.
    """
    return await queue.submit(task_id, result_json)


@server.tool()
async def fail_task(task_id: str, reason: str) -> dict:
    """Report that you cannot complete a task, so the agents can fall back immediately."""
    return {"ok": await queue.fail(task_id, reason)}


@server.tool()
async def upload_artifact(task_id: str, filename: str, content_base64: str) -> dict:
    """Upload a file you produced for a task (DOCX, PDF, XLSX, PPTX; max 10 MB), base64-encoded.

    Returns {url}. Include the url in your submitted result.
    """
    try:
        data = base64.b64decode(content_base64, validate=False)
    except Exception as e:
        return {"error": f"invalid base64: {e}"}
    if len(data) > MAX_ARTIFACT_BYTES:
        return {"error": "file too large (max 10 MB)"}
    async with SessionLocal() as db:
        t = await db.get(WorkbuddyTask, task_id)
        if not t:
            return {"error": "unknown task_id"}
        kind = "report" if t.skill == "report_builder" else "other"
        a = Artifact(session_id=t.session_id, task_id=task_id, kind=kind, filename=filename[:200], url="",
                     size_bytes=len(data), content_type=mimetypes.guess_type(filename)[0], data=data)
        db.add(a)
        await db.flush()
        a.url = f"{settings.public_base_url.rstrip('/')}/artifacts/{a.id}"
        await db.commit()
        return {"url": a.url}


mcp_http_app = server.streamable_http_app(
    stateless_http=True,
    host="0.0.0.0",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def require_api_key(app):
    """ASGI wrapper: /mcp requires X-API-Key == MCP_API_KEY (constant-time compare)."""
    async def wrapped(scope, receive, send):
        if scope["type"] == "http":
            headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            given = headers.get("x-api-key", "")
            if not settings.mcp_api_key or not hmac.compare_digest(given, settings.mcp_api_key):
                await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)
    return wrapped
