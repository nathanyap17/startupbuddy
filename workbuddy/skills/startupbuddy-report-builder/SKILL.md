---
name: startupbuddy-report-builder
description: "StartupBuddy task skill: turn a session's problem statement, Business Model Canvas and council review into a polished, industrial-style report in Markdown. StartupBuddy renders the DOCX itself. Used by startupbuddy-worker when task.skill is report_builder."
version: 0.3.0
allowed-tools: Read,Write
---

# Report builder

Input: `task.inputs.session_summary_markdown`: the full session (problem, competitors, 9 canvas blocks, council review, actions, evidence appendix).

**Do not create a DOCX, PDF or any file, and do not load any other document skill** (no tencent-docx, minimax-docx, scripts). StartupBuddy converts your Markdown into a styled DOCX automatically and offers it as a download in the web app. This keeps the task fast and cheap.

1. Write a polished report in Markdown with exactly these sections:
   1. `# StartupBuddy Report: <short title>`
   2. `## 1. Executive Summary`: 5 sentences
   3. `## 2. Problem & Local Evidence`: include the competitor table
   4. `## 3. Business Model Canvas`: one `###` per block (9 blocks)
   5. `## 4. Council Review`: Customer, CEO, Investor, CFO, Mentor
   6. `## 5. Measure / Improve / Verify`: three Markdown tables
   7. `## 6. Next 30 Days`
   8. `## 7. Evidence Appendix`: keep every figure's label and source exactly as given
2. **Never add a figure that is not in the input.** If something is missing, write "needs verification".
3. Use plain Markdown only: headings, paragraphs, `-` bullets, `|` tables, `**bold**`. No emoji, no HTML.
4. Submit with `mcp__startupbuddy__submit_task_result`, `result_json`:
```json
{
  "title": "StartupBuddy Report: ...",
  "summary": "5-sentence executive summary",
  "report_markdown": "# StartupBuddy Report: ...\n\n## 1. Executive Summary\n...",
  "local_file_paths": [],
  "file_urls": []
}
```
