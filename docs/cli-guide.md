# CLI guide

`meridian_expert` exposes a Typer CLI via `meridian-expert`.

## Health and setup

### Doctor

```bash
meridian-expert doctor
```

Reports workspace/config parse status, OpenAI key presence, and repository readiness for real local investigation.

## Task commands

### Create

```bash
meridian-expert task create <task_md> [--attachment <file> ...] [--related-task-id <id>] [--parent-task-id <id>]
```

Creates a task (`T-*`), initializes cycle `C01`, stores task input/attachments, and emits initial triage artifacts.

### Show

```bash
meridian-expert task show <task_id> [--evidence-summary]
```

Prints task metadata; with `--evidence-summary`, includes selected anchors/bundles/tests and route/risk hints.

### Status

```bash
meridian-expert task status <task_id>
```

Prints state and current cycle.

### Run

```bash
meridian-expert task run <task_id> --to-gate
meridian-expert task run <task_id> --through-delivery
```

- `--to-gate` runs through review gating and stops for manual review
- `--through-delivery` additionally requires approved review items and writes delivery artifacts

### Clarify

```bash
meridian-expert task clarify <task_id> "<message>"
```

Appends clarification response, updates triage artifacts/state.

### Redirect

```bash
meridian-expert task redirect <task_id> "<message>" [--new-cycle]
```

Records redirection and optionally starts a new cycle.

### Follow-on

```bash
meridian-expert task follow-on <source_task_id> <task_md>
```

Creates a child task from a delivered source task.

## Review commands

### Queue

```bash
meridian-expert review queue [--status pending|approved|rejected|all] [--task-id <task_id>]
```

Lists review items.

### Decide

```bash
meridian-expert review decide <review_id> approve
meridian-expert review decide <review_id> reject
```

Updates review item status.

## Compatibility commands

### Check

```bash
meridian-expert compat check --changed-file <path> [--changed-file <path> ...] [--markdown-report]
```

Computes compatibility impact from changed paths using manifest relationships.

## Bundle commands

### List and show

```bash
meridian-expert bundle list
meridian-expert bundle show <bundle_name>
```

## Learning and exemplar commands

### Learning

```bash
meridian-expert learning nominate <task_id>
meridian-expert learning list [--status pending|approved|rejected|all]
meridian-expert learning decide <candidate_id> approve
```

### Exemplar

```bash
meridian-expert exemplar nominate <task_id>
meridian-expert exemplar list [--status pending|approved|rejected|all]
meridian-expert exemplar decide <candidate_id> reject
```

Prototype deliveries are intentionally ineligible for nomination.
