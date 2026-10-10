---
name: startupbuddy-report-builder
description: "StartupBuddy task skill: turn a session's problem statement, Business Model Canvas and council review into a polished, industrial-style report (Markdown + DOCX). Used by startupbuddy-worker when task.skill is report_builder."
version: 0.2.0
allowed-tools: Read,Write,Bash
---

# Report builder

Input: `task.inputs.session_summary_markdown`: the full session (problem, competitors, 9 canvas blocks, council review, actions, evidence appendix).

1. Write a polished report in Markdown with these sections:
   1. Executive summary (5 sentences)
   2. Problem & local evidence
   3. Business Model Canvas (all 9 blocks)
   4. Council review (Customer, CEO, Investor, CFO, Mentor)
   5. **Measure / Improve / Verify** (three tables)
   6. Next 30 days
   7. Evidence appendix: keep every figure's label and source exactly as given
2. **Never add a figure that is not in the input.** If something is missing, write "needs verification".
3. Save it as a DOCX in the current workspace folder (use the **minimax-docx** skill if available), named `StartupBuddy-Report-<short-title>.docx`.
4. Submit with `mcp__startupbuddy__submit_task_result`, `result_json`:
```json
{
  "title": "StartupBuddy Report: ...",
  "summary": "5-sentence executive summary",
  "report_markdown": "# ... full report ...",
  "local_file_paths": ["C:\\...\\StartupBuddy-Report-....docx"],
  "file_urls": []
}
```
