"""Shared helpers: run one ADK LlmAgent with a timeout, log every tool call to agent_event,
and parse the structured output (google-adk skill patterns 1, 7, 9)."""
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


def tool_logging(session_id: str, agent: str, target: str | None):
    starts: dict[str, float] = {}

    async def before(tool, args, tool_context):
        starts[tool.name] = time.perf_counter()
        await emit(session_id, agent, "tool_call", f"{tool.name}({_short(args)})", target=target,
                   detail={"tool": tool.name, "args": args})
        return None

    async def after(tool, args, tool_context, tool_response):
        ms = int((time.perf_counter() - starts.pop(tool.name, time.perf_counter())) * 1000)
        await emit(session_id, agent, "tool_result", f"{tool.name} → {_short(tool_response, 160)}", target=target,
                   detail={"tool": tool.name}, latency_ms=ms)
        return None

    return before, after


def _short(obj: Any, n: int = 120) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str) if not isinstance(obj, str) else obj
    return s if len(s) <= n else s[: n - 1] + "…"


def make_agent(name: str, instruction: str, output_schema: type[BaseModel], session_id: str,
               target: str | None = None, tools: list | None = None) -> LlmAgent:
    before, after = tool_logging(session_id, name, target)
    return LlmAgent(
        name=name,
        model=settings.gemini_model,
        instruction=instruction,
        tools=tools or [],
        output_schema=output_schema,
        before_tool_callback=before,
        after_tool_callback=after,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.4,
            thinking_config=types.ThinkingConfig(thinking_level=settings.thinking_level)),
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


async def run_agent(agent: LlmAgent, prompt: str, schema: type[T], session_id: str,
                    target: str | None = None, timeout_s: int | None = None) -> T:
    """Run the agent to completion and return its validated structured output."""
    runner = InMemoryRunner(agent=agent, app_name=APP)
    sess = await runner.session_service.create_session(app_name=APP, user_id="demo")
    await emit(session_id, agent.name, "start", f"{agent.name} started", target=target)
    t0 = time.perf_counter()
    final: list[str] = []

    async def _go():
        msg = types.Content(role="user", parts=[types.Part(text=prompt)])
        async for ev in runner.run_async(user_id="demo", session_id=sess.id, new_message=msg):
            if ev.content and ev.content.parts and ev.is_final_response():
                txt = "".join(p.text or "" for p in ev.content.parts if not getattr(p, "thought", False))
                if txt.strip():
                    final.append(txt)

    try:
        await asyncio.wait_for(_go(), timeout=timeout_s or settings.agent_turn_timeout_s)
        if not final:
            raise RuntimeError("agent returned no final text")
        out = _parse(final[-1], schema)
    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        await emit(session_id, agent.name, "error", f"{agent.name} failed: {type(e).__name__}: {str(e)[:200]}",
                   target=target, latency_ms=ms)
        raise
    ms = int((time.perf_counter() - t0) * 1000)
    await emit(session_id, agent.name, "done", f"{agent.name} finished", target=target, latency_ms=ms)
    return out
