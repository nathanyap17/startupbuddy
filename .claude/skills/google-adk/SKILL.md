---
name: google-adk
description: Reference for building agents with Google ADK (Agent Development Kit) in Python. Use whenever writing or modifying agent code - LlmAgent, LoopAgent, SequentialAgent, ParallelAgent, FunctionTool, AgentTool, sub_agents, session state, callbacks, runners, or LiteLLM/Gemini model integration. Also use when debugging agent loops that don't terminate, tools the model ignores or calls with missing arguments, or model configuration errors.
---

# Google ADK reference

## Local source of truth

The official docs and source are cloned next to this repo, at the same version as the installed `google-adk`. **Read them rather than relying on memory**; the API changes between releases.

```
../adk-docs/      # documentation (markdown; llms-full.txt = everything in one file)
../adk-python/    # source, checked out at the installed version's tag
```

**Lookup order:**
1. `../adk-docs/docs/agents/`, `../adk-docs/docs/tools/`, `../adk-docs/docs/sessions/`: concepts and recommended patterns
2. `../adk-python/src/google/adk/agents/`: real class signatures
3. `../adk-python/src/google/adk/tools/`: how tools are wrapped and invoked
4. Only then, general knowledge

```bash
grep -rn "class LoopAgent" ../adk-python/src/
grep -rn "max_iterations\|escalate" ../adk-python/src/google/adk/agents/
grep -rn "_prepare_invocation_args" ../adk-python/src/google/adk/tools/
```

## Choosing an agent type

| Type | Use |
|---|---|
| `LlmAgent` / `Agent` | Reasoning, routing, choosing tools |
| `LoopAgent` | Repeat sub-agents until one escalates or `max_iterations` is reached |
| `SequentialAgent` | A fixed pipeline; sub-agents pass results through session state (`output_key`) |
| `ParallelAgent` | Independent work fanned out at once |
| `AgentTool(agent=…)` | Let a parent call an agent as a bounded step and keep control afterwards (works for LoopAgents too) |

## Patterns that hold up

1. **Every loop is bounded.** Always set `max_iterations`, and give it an `escalate` path. An unbounded loop hangs a demo.
2. **Termination is decided by code, not the model.** A small `BaseAgent` checker reads real state (database, files) and yields `Event(actions=EventActions(escalate=done))`. The model only decides what to say or do next.
3. **Tool parameters are flat.** Give tool functions scalar or list parameters (`def get_weather(farm_id: str)`), not a single Pydantic model as the whole parameter. In some ADK versions a lone `req: SomeModel` parameter is flattened into the schema the model sees but not rebuilt before the call, so every call fails with "mandatory input parameters are not present". Check `FunctionTool._prepare_invocation_args` in the installed source before relying on model parameters. Return Pydantic models freely.
4. **Docstrings are the tool description the model reads.** Say what it does, when to call it, what each argument means, and what it returns. Vague docstrings cause skipped or misused tools.
5. **Data the machine already has never comes from the model.** Load graphs, records and configuration inside the tool from the database; the model passes only an id.
6. **Wrap tools with an error boundary** that returns a structured error the model can read, instead of raising and killing the run.
7. **Bound every model turn** with `asyncio.wait_for(…, timeout=…)` and have a deterministic fallback when it times out or returns unparseable output.
8. **Guard the output.** After the run, validate what the model produced against your rules (known ids, allowed actions, dates) and correct or drop anything outside them. Log each correction.
9. **Log every tool call** (`before_tool_callback` / `after_tool_callback`): name, args, latency, result summary. It's your audit trail and your demo evidence.
10. **Need a sub-agent's intermediate outputs?** `AgentTool` returns only the final text. Run the sub-agent with its own `InMemoryRunner` and read `session.state` afterwards.

## Models (StartupBuddy)

StartupBuddy calls Gemini on Vertex AI **natively** (no LiteLLM): ADK reads the model string and uses Vertex when these env vars are set.
```python
import os
from google.adk.agents import LlmAgent
agent = LlmAgent(name="bmc_customer_segments", model=os.environ["GEMINI_MODEL"], ...)
# env: GOOGLE_GENAI_USE_VERTEXAI=TRUE, GOOGLE_CLOUD_PROJECT=dormathon-workspace-1,
#      GOOGLE_CLOUD_LOCATION=<region where the model is served>, GEMINI_MODEL=<explicit id, EXP-4>
```
Pin an explicit model id (never `*-latest`). Model region may differ from the Cloud Run region (`asia-southeast1`); confirm availability in EXP-4.

**Pinned version:** `google-adk==2.6.1` at clone time (2026-10-10); `v2.11.0` exists. If the project venv upgrades, rerun `setup_adk_refs.sh` so `../adk-python` matches.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Loop never ends | No escalate and no `max_iterations` | Set both |
| Model ignores a tool | Vague docstring | Rewrite it for the model |
| "mandatory input parameters are not present" | Single-model parameter not rebuilt | Use flat parameters |
| Model calls dependent tools in parallel | No ordering instruction | Instruct "one tool at a time; wait for results"; clamp bad inputs in the tool |
| Run hangs on a local model | No timeout | `wait_for` + deterministic fallback |
| State lost between steps | Not using session state / `output_key` | See `../adk-docs/docs/sessions/` |

## Before writing agent code

1. Grep the signature in `../adk-python/src/`.
2. Check `../adk-docs/` for the current recommended pattern.
3. Confirm the tool's input/output models exist and parameters are flat.
4. Confirm every loop has `max_iterations` and a code-based checker.
