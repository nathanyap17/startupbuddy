---
name: startupbuddy-report-builder
description: StartupBuddy task skill. Turn a session's problem statement, Business Model Canvas and council verdict into an industrial-style DOCX/PDF report. Used by the startupbuddy-worker loop when task.skill is report_builder.
---

# Report builder (DRAFT)

Inputs: `session_summary_markdown`, `evidence[]`, `council_verdict`.
Sections: Executive summary · Problem & evidence · Business Model Canvas (9 blocks) · Council review (5 seats) · **Measure / Improve / Verify** tables · Next 30 days · Evidence appendix (every figure with its label and source).
Produce DOCX (and PDF if available). `upload_artifact` each file. Output `{title, sections[], artifact_kinds[]}`.
Never add a figure that is not in `evidence[]`; if needed, mark it `needs_verification`.
