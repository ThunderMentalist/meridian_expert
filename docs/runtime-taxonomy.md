# Runtime taxonomy

## Core entities

### Task

A task is the top-level unit of work, identified as `T-YYYYMMDD-####`.

### Cycle

A cycle is a scoped pass through the lifecycle for the same task (`C01`, `C02`, ...). Redirection can start a new cycle without creating a new task.

### Delivery

A delivery is a produced answer package (`D01`, ...), gated by review.

## Lifecycle stages vs states

- **Lifecycle stage mode** (prototype/warm-up/mature/shock) controls artifact naming and delivery namespace.
- **Task state** tracks runtime progression (`TRIAGED`, `INVESTIGATING`, `IN_REVIEW`, etc.).

Current config maps all families to `prototype` mode.

## Prototype naming rules

When lifecycle stage is `prototype`:

- cycle artifacts are under `cycles/<cycle>/prototype/...`
- filenames include `.prototype` suffixes (for example `task_brief.prototype.md`, `answer_draft.prototype.md`)
- delivery paths are under `deliveries/prototype/<delivery_id>/`
- snippet filenames in delivery include `.prototype.py`

These markers make prototype outputs explicit and prevent accidental conflation with mature outputs.

## Task-family taxonomy

Supported families:

- `theory`
- `usage`
- `updates`
- `builder` (disabled by default)

Builder remains scaffolded but excluded from normal routing unless explicitly enabled.

## Review and nomination taxonomy

- Review items: `task_brief` and `draft`
- Learning candidates: `LC-<task_id>`
- Exemplar candidates: `EC-<task_id>`

Prototype deliveries are ineligible for learning/exemplar nomination by design.
