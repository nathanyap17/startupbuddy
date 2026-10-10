"""Session Assistant: conversational Q&A grounded in one session's context (web chat + WorkBuddy ask_session)."""
import json
from typing import Any

from sqlalchemy import select

from app.agent import prompts
from app.agent.common import make_agent, run_agent_text
from app.agent.factories import knowledge_tool
from app.db import SessionLocal
from app.events import emit
from app.models import ChatMessage


async def _context(session_id: str) -> dict[str, Any]:
    from app.routers.sessions import session_detail
    d = await session_detail(session_id)
    return {
        "phase": d["phase"], "intent": d["intent"], "location": d["location_text"],
        "problem": d["problem"], "canvas": {b["key"]: b.get("content") for b in d["blocks"] if b.get("content")},
        "council_verdict": d["verdict"],
        "council": [{k: r[k] for k in ("seat", "verdict", "risks", "must_verify", "improve")} for r in d["council"]],
        "evidence": d["evidence"][:40],
        "actions": [{k: a[k] for k in ("title", "kind", "approval", "source_agent")} for a in d["actions"]],
        "pilot_summary": d.get("summary"),
    }


async def ask(session_id: str, question: str, channel: str = "web") -> dict[str, Any]:
    question = question.strip()[:2000]
    async with SessionLocal() as db:
        history = (await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id)
                                    .order_by(ChatMessage.created_at.desc()).limit(10))).scalars().all()
        db.add(ChatMessage(session_id=session_id, role="user", content=question, channel=channel))
        await db.commit()
    await emit(session_id, "founder", "chat", question, detail={"role": "user", "channel": channel})
    ctx = await _context(session_id)
    prompt = json.dumps({
        "session_context": ctx,
        "recent_conversation": [{"role": m.role, "content": m.content} for m in reversed(history)],
        "founder_question": question,
    }, ensure_ascii=False, default=str)
    agent = make_agent("session_assistant", prompts.ASSISTANT, None, session_id, "chat", [knowledge_tool()])
    try:
        reply = (await run_agent_text(agent, prompt, session_id, "chat", timeout_s=40, announce=False)).strip()
    except Exception:
        reply = "😅 Sorry, I couldn't think that through just now. Could you try asking again in a moment?"
    async with SessionLocal() as db:
        db.add(ChatMessage(session_id=session_id, role="assistant", content=reply, channel=channel))
        await db.commit()
    await emit(session_id, "session_assistant", "chat", reply, detail={"role": "assistant", "channel": channel})
    return {"reply": reply}
