# Review, learning, and exemplars

## Review gates

The system creates review items during lifecycle execution:

- `task_brief` gate
- `draft` gate

In prototype mode, delivery is blocked until all review items are approved and no item is rejected.

## Approval and blocking behavior

- rejected review items move task state to `BLOCKED`
- approved items can advance gate readiness
- `task run --through-delivery` enforces gate readiness before producing delivery artifacts

This preserves human supervision for prototype outputs.

## Prototype exclusions

Prototype deliveries are excluded from both:

- learning candidate nomination
- exemplar candidate nomination

Nomination commands intentionally fail for prototype-only deliveries to avoid polluting reusable knowledge with unvalidated prototype artifacts.

## Learning candidate flow

- nominate: `LC-<task_id>` created for eligible delivered tasks
- list by status
- approve/reject decisions recorded

## Exemplar candidate flow

- nominate: `EC-<task_id>` created for eligible delivered tasks
- list by status
- approve/reject decisions recorded

## Why this matters

This split lets teams:

- iterate quickly in prototype mode
- keep strict quality control over what becomes reusable institutional memory
- preserve an auditable decision trail for approvals/rejections
