---
name: startupbuddy-desk-research
description: StartupBuddy task skill. Desk research on a business idea in a Malaysian location - market demand, competitors, pricing, regulations - returning sourced JSON. Used by the startupbuddy-worker loop when task.skill is desk_research.
---

# Desk research (DRAFT, validate in EXP-3)

Inputs: `intent`, `location`, `questions[]`, `known_competitors[]`.
1. Web-search each question, preferring government (gov.my, DOSM/OpenDOSM, SSM, SME Corp, state/council sites), reputable news and research.
2. For each finding record `{claim, value, label, source_url, method}`. Use `sourced` only with a URL you opened.
3. Note trends and why-now signals; note anything contradicting the idea.
Output (JSON, must match `output_schema`): `{findings[], competitors[], regulations[], open_questions[]}`.
