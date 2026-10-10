---
name: startupbuddy-financial-sheet
description: StartupBuddy task skill. Build an XLSX with startup costs, monthly fixed/variable costs, pricing and break-even from a session's cost and revenue blocks. Used by the startupbuddy-worker loop when task.skill is financial_sheet.
---

# Financial sheet (DRAFT)

Inputs: `revenue_streams`, `cost_structure`, `assumptions[]` (each labelled).
Sheets: Assumptions (with label column) · Startup costs · Monthly P&L (12 months) · Break-even (formula cells, not pasted values).
`upload_artifact`; output `{break_even_units_per_month, monthly_fixed_cost_rm, assumptions_used[]}` (all labelled `estimated` with method).
