---
name: startupbuddy-rules
description: Non-negotiable rules for StartupBuddy. Use whenever writing code that touches Google Workspace actions (calendar, email, drive), evidence or figures shown to users, stakeholder/contact data, the WorkBuddy task queue or MCP tools, agent loops, or secrets/config.
---

# StartupBuddy rules

These are commitments made to judges and users. Enforce them in code, not by prompt wording alone.

## 1 · No outward action without explicit approval; emails are drafts
**Why:** judges and users must trust that the agent never acts on their behalf unasked. The demo shows the approval gate on purpose.
**Right:**
```python
async def create_gmail_draft(action_id: str) -> dict:
    action = await repo.get_action(action_id)
    if action.approval != ApprovalStatus.approved:
        return {"error": "action_not_approved", "action_id": action_id}
    draft = gmail.users().drafts().create(userId="me", body=build_draft(action.payload)).execute()
    await repo.mark_executed(action_id, external_ref=draft["id"])
```
**Wrong:**
```python
gmail.users().messages().send(userId="me", body=msg).execute()   # sends; no approval check
```

## 2 · Every figure carries an evidence label
**Why:** "verifiable results" is a judging criterion; one invented number discredits the report.
**Right:**
```python
EvidenceItem(claim="Kolo mee stalls within 500 m", value="7", label="sourced",
             source_url=places_url, produced_by="problem_coordinator")
EvidenceItem(claim="Daily covers at break-even", value="85", label="estimated",
             method="fixed costs / (price - unit cost)", produced_by="council_cfo")
```
**Wrong:** a report paragraph saying "the market is worth RM 2 billion" with no `EvidenceItem` behind it. The DB `CHECK` constraints also reject `sourced` without URL and `estimated` without method.

## 3 · No scraping personal contact data
**Why:** privacy (PDPA 2010) and trust. "Connect with stakeholders" means public organisations and programmes from `knowledge/`, or people the user types in.
**Right:** `key_partners` proposes "SME Corp Sarawak office – business advisory", with the URL from `kb_document`.
**Wrong:** a tool that searches LinkedIn/Google for named investors' emails and puts them in `action_item.payload.attendees`.

## 4 · Agents never block forever on WorkBuddy
**Why:** WorkBuddy runs on a laptop; it may be offline. A hung demo is worse than a labelled fallback.
**Right:**
```python
result = await queue.wait_for(task_id, timeout=settings.WORKBUDDY_TASK_DEADLINE_S)
if result is None:
    await events.emit(session_id, agent, kind="fallback", summary="WorkBuddy task expired; using agent-only research")
    mark_related_evidence(session_id, label="needs_verification")
```
**Wrong:** `while not task.done: await asyncio.sleep(1)` with no deadline.

## 5 · MCP tools return within 25 s
**Why:** WorkBuddy expects tool responses within ~30 s.
**Right:** `await_next_task(wait_s)` clamps `wait_s = min(wait_s, 25)` and returns `{"task": None}` on timeout.
**Wrong:** a `run_full_pipeline` MCP tool that awaits the whole run.

## 6 · Loops are bounded; termination decided by code
**Right:** council revision `round < 2` checked from `startup_session.revision_round`; every `LoopAgent(max_iterations=…)`.
**Wrong:** letting the council LLM decide "revise again" with no counter.

## 7 · Secrets never in repo or docs
**Right:** `os.environ["MAPS_API_KEY"]`; names only in `docs/CREDENTIALS.md`.
**Wrong:** committing `token.json`, `maps-api.key`, `.env`, or pasting a key into a doc.


## 8 · Understand before planning (Phase 0 guardrail)
**Why:** "I want to sell drugs" was once planned as a pharmacy. Never assume the convenient reading of risky words.
**Right:** the intake screener classifies the intent; `RISK` words force a G0 clarification; `ILLEGAL` words block with the law cited; G0 is never auto-approved, even with Always allow.
**Wrong:** letting the coordinator start Phase 1 on an ambiguous or illegal intent, or auto-approving G0.

## 9 · Follow-ups act only inside the founder's own space
**Why:** the founder approved "draft the email, then schedule when they reply"; inviting third parties is outward action they did not approve.
**Right:** a reply that proposes a time creates an event in the founder's calendar with **no attendees** (Meet link only if the reply says online), and the feed says so.
**Wrong:** adding the sender as an attendee, sending a reply email, or booking a Meet for an in-person F&B meet-up.
