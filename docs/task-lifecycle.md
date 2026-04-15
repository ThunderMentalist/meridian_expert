# Task lifecycle

## 1) Triage

`task create` ingests task markdown, generates a triage brief, and initializes state:

- `NEEDS_CLARIFICATION` when ambiguity is detected
- otherwise `TRIAGED`

Triage captures suggested bundles, anchor files, and cross-repo hints.

## 2) Clarification

If clarification is needed, a clarification request artifact is generated. `task clarify` appends user clarification, rewrites brief artifacts, and transitions back toward `TRIAGED` when questions are resolved.

## 3) Investigation

`task run --to-gate` moves to investigation:

- validates repository readiness for real investigations
- blocks with a written blocker artifact if required siblings are missing
- otherwise builds evidence from ranked bundles and writes an evidence bundle artifact

Investigation is anchor-first but expands through route-aware coupling rules.

## 4) Draft generation

Family-specific generation produces:

- answer draft
- optional appendix draft
- optional snippets (syntax-validated)

Usage family can include attachment text processing.

## 5) Review

Review artifacts and structured review decisions are generated. In prototype mode with required review, task remains blocked at gate (`IN_REVIEW`) until humans approve pending review items.

## 6) Delivery

`task run --through-delivery` requires all review items approved. Delivery writes final answer/appendix/manifest artifacts and transitions task to `DELIVERED`.

## 7) Redirection

`task redirect` records direction changes. With `--new-cycle`, the same task continues in a new cycle (`C+1`) rather than creating a separate task.

## 8) Follow-on tasks

`task follow-on <source_task>` creates a new task linked to a delivered parent task. Follow-on creation is rejected unless the source task is already delivered.
