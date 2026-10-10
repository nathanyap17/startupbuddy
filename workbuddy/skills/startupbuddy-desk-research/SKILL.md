---
name: startupbuddy-desk-research
description: "StartupBuddy task skill: desk research on a business idea in a Malaysian location (demand, prices and costs in RM, licences, trends), returned as labelled JSON. Used by startupbuddy-worker when task.skill is desk_research."
version: 0.2.0
allowed-tools: Read,Write,Bash
---

# Desk research

Input: `task.inputs` = `{intent, location, questions[]}`. Keep it fast: aim to finish within 3 minutes.

1. Web-search each question. Prefer Malaysian government sources (gov.my, DOSM/OpenDOSM, SSM, SME Corp, state and local council sites), reputable Malaysian news and research.
2. Record each finding as `{claim, value, label, source_url, method}`:
   - `sourced` only with a URL you opened;
   - `estimated` with a `method`;
   - otherwise `needs_verification`.
3. Note competitors you found, regulations/licences, and open questions.

Submit with `mcp__startupbuddy__submit_task_result`, `result_json` exactly in this shape:
```json
{
  "findings":      [{"claim": "...", "value": "...", "label": "sourced", "source_url": "https://...", "method": null}],
  "competitors":   [{"name": "...", "note": "...", "source_url": "https://..."}],
  "regulations":   [{"claim": "...", "value": null, "label": "sourced", "source_url": "https://...", "method": null}],
  "open_questions": ["..."]
}
```
Aim for 5–10 findings and 2–5 regulations.
