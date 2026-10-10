"""Shared helpers: run one ADK LlmAgent with a timeout, stream its thinking and every tool call to
agent_event, and parse the structured output (google-adk skill patterns 1, 7, 9)."""
import asyncio
import json
import logging
import re
import time
from typing import Any, TypeVar

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.events import emit

log = logging.getLogger("startupbuddy.agent")
T = TypeVar("T", bound=BaseModel)
APP = "startupbuddy"

# Friendly names + emoji for the live feed (humanised event stream).
AGENT_LABEL: dict[str, tuple[str, str]] = {
    "problem_coordinator": ("🧭", "Problem Coordinator"),
    "customer_segments": ("👥", "Customer Segments"), "value_propositions": ("💎", "Value Propositions"),
    "channels": ("📣", "Channels"), "customer_relationships": ("🤝", "Customer Relationships"),
    "key_activities": ("🛠️", "Key Activities"), "key_resources": ("🧰", "Key Resources"),
    "key_partners": ("🔗", "Key Partners"), "revenue_streams": ("💰", "Revenue Streams"),
    "cost_structure": ("🧾", "Cost Structure"),
    "council_customer": ("🛒", "Council · Customer"), "council_ceo": ("🧑‍💼", "Council · CEO"),
    "council_investor": ("📈", "Council · Investor"), "council_cfo": ("🧮", "Council · CFO"),
    "council_mentor": ("🧑‍🏫", "Council · Local Mentor"), "advisor": ("🗓️", "Advisor"),
    "session_assistant": ("💬", "StartupBuddy"), "pilot_summary": ("✨", "Pilot Summary"),
}
TOOL_SOURCE = {"find_nearby_places": "Google Places", "search_knowledge": "Knowledge base"}
TOOL_VERB = {"find_nearby_places": "🔎 Scouting Google Maps for", "search_knowledge": "📚 Looking up"}


def label(agent: str) -> str:
    e, n = AGENT_LABEL.get(agent, ("🤖", agent.replace("_", " ").title()))
    return f"{e} {n}"


def tool_logging(session_id: str, agent: str, target: str | None):
    starts: dict[str, float] = {}

    async def before(tool, args, tool_context):
        starts[tool.name] = time.perf_counter()
        q = args.get("query") or _short(args)
        await emit(session_id, agent, "tool_call", f"{TOOL_VERB.get(tool.name, '🔧 Calling ' + tool.name)} “{q}”",
                   target=target, detail={"tool": tool.name, "args": args, "source": TOOL_SOURCE.get(tool.name)})
        return None

    async def after(tool, args, tool_context, tool_response):
        ms = int((time.perf_counter() - starts.pop(tool.name, time.perf_counter())) * 1000)
        sources: list[str] = []
        summary = _short(tool_response, 140)
        if tool.name == "search_knowledge":
            res = (tool_response or {}).get("results", [])
            sources = sorted({r.get("publisher") or r.get("title", "") for r in res if r})
            summary = f"Found {len(res)} reference(s)" + (f" from {', '.join(sources)}" if sources else " (nothing matched)")
        elif tool.name == "find_nearby_places":
            places = (tool_response or {}).get("places", [])
            sources = ["Google Places"]
            summary = f"Found {len(places)} places nearby" + (f", closest: {places[0]['name']} ({places[0]['distance_km']} km)" if places else "")
        await emit(session_id, agent, "tool_result", summary, target=target,
                   detail={"tool": tool.name, "sources": sources}, latency_ms=ms)
        return None

    return before, after


def _short(obj: Any, n: int = 120) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str) if not isinstance(obj, str) else obj
    return s if len(s) <= n else s[: n - 1] + "…"


def make_agent(name: str, instruction: str, output_schema: type[BaseModel] | None, session_id: str,
               target: str | None = None, tools: list | None = None) -> LlmAgent:
    before, after = tool_logging(session_id, name, target)
    kwargs: dict[str, Any] = {}
    if output_schema is not None:
        kwargs["output_schema"] = output_schema
    return LlmAgent(
        name=name,
        model=settings.gemini_model,
        instruction=instruction,
        tools=tools or [],
        before_tool_callback=before,
        after_tool_callback=after,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.4,
            # include_thoughts streams Gemini's thought summaries: the real "brainstorming" in the feed.
            thinking_config=types.ThinkingConfig(thinking_level=settings.thinking_level, include_thoughts=True)),
        **kwargs,
    )


def _parse(text: str, schema: type[T]) -> T:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return schema.model_validate_json(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            raise
        return schema.model_validate_json(m.group(0))


async def run_agent_text(agent: LlmAgent, prompt: str, session_id: str, target: str | None = None,
                         timeout_s: int | None = None, announce: bool = True) -> str:
    """Run the agent to completion; stream thought summaries; return its final text."""
    runner = InMemoryRunner(agent=agent, app_name=APP)
    sess = await runner.session_service.create_session(app_name=APP, user_id="demo")
    if announce:
        await emit(session_id, agent.name, "start", f"{label(agent.name)} is on it", target=target)
    t0 = time.perf_counter()
    final: list[str] = []

    async def _go():
        msg = types.Content(role="user", parts=[types.Part(text=prompt)])
        async for ev in runner.run_async(user_id="demo", session_id=sess.id, new_message=msg):
            if not (ev.content and ev.content.parts):
                continue
            for p in ev.content.parts:
                if getattr(p, "thought", False) and p.text and p.text.strip():
                    await emit(session_id, agent.name, "thinking", p.text.strip()[:900], target=target)
            if ev.is_final_response():
                txt = "".join(p.text or "" for p in ev.content.parts if not getattr(p, "thought", False))
                if txt.strip():
                    final.append(txt)

    try:
        await asyncio.wait_for(_go(), timeout=timeout_s or settings.agent_turn_timeout_s)
        if not final:
            raise RuntimeError("agent returned no final text")
    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        await emit(session_id, agent.name, "error", f"😓 {label(agent.name)} hit a snag: {type(e).__name__}",
                   target=target, latency_ms=ms)
        raise
    if announce:
        ms = int((time.perf_counter() - t0) * 1000)
        await emit(session_id, agent.name, "done", f"✅ {label(agent.name)} done", target=target, latency_ms=ms)
    return final[-1]


async def run_agent(agent: LlmAgent, prompt: str, schema: type[T], session_id: str,
                    target: str | None = None, timeout_s: int | None = None) -> T:
    """Run the agent to completion and return its validated structured output."""
    text = await run_agent_text(agent, prompt, session_id, target, timeout_s)
    try:
        return _parse(text, schema)
    except Exception as e:
        await emit(session_id, agent.name, "error", f"😓 {label(agent.name)} returned an unreadable answer",
                   target=target, detail={"error": str(e)[:300]})
        raise
