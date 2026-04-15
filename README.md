# meridian_expert

`meridian_expert` is a CLI-first, review-gated prototype expert system for Meridian ecosystem analysis. It helps with **theory**, **usage**, and **update-impact** tasks, while preserving an auditable task lifecycle and artifact trail.

It is designed around two adjacent repositories at runtime:

- `../meridian` (distribution name: `google-meridian`, import package: `meridian`)
- `../meridian_aux` (tightly coupled companion repo)

During Codex development and default tests, cross-repo behavior is validated with **embedded registries** and **synthetic fixture repositories**. At runtime with human users, it is intended to operate against real local sibling repositories when available.

## Runtime workspace layout

Expected layout (default):

```text
workspace/
  meridian/
  meridian_aux/
  meridian_expert/
```

`meridian_expert` writes runtime artifacts and SQLite state under `runtime/` by default.

## Install

```bash
python -m pip install -e .[dev]
```

## Environment variables

Primary path and backend controls:

- `MERIDIAN_REPO_PATH` (default from `config/repos.example.yaml`, fallback `../meridian`)
- `MERIDIAN_AUX_REPO_PATH` (fallback `../meridian_aux`)
- `MERIDIAN_EXPERT_WORKSPACE` (fallback `./runtime`)
- `MERIDIAN_EXPERT_LLM_BACKEND` (`openai` default, `fake` for deterministic offline mode)
- `OPENAI_API_KEY` (required only for real OpenAI backend usage)

Path precedence:

1. CLI override arguments passed into settings resolution
2. environment variables
3. `config/repos.local.yaml`
4. `config/repos.example.yaml`
5. built-in sibling defaults (`../meridian`, `../meridian_aux`, `./runtime`)

## Quickstart

Use deterministic offline backend + synthetic fixtures for local smoke runs:

```bash
export MERIDIAN_EXPERT_LLM_BACKEND=fake
meridian-expert doctor
meridian-expert task create demo/tasks/theory_adstock/task.md
meridian-expert task run T-YYYYMMDD-0001 --to-gate
meridian-expert review queue --status pending
```

Approve review items, then deliver:

```bash
meridian-expert review decide R-<task>-<cycle>-task_brief approve
meridian-expert review decide R-<task>-<cycle>-draft approve
meridian-expert task run <task_id> --through-delivery
```

## Lifecycle overview

The task state machine moves through:

`NEW/NEEDS_CLARIFICATION → TRIAGED → INVESTIGATING → DRAFT_READY → IN_REVIEW → DELIVERED (or BLOCKED)`.

Key lifecycle behavior:

- triage can request clarification and generate clarification artifacts
- investigation is anchor-first and bundle-guided
- delivery is review-gated
- redirection can keep the same task and start a new cycle
- follow-on tasks require a delivered source task

See `docs/task-lifecycle.md` and `docs/runtime-taxonomy.md`.

## Offline / fake-backend path

Offline behavior is a first-class mode:

- set `MERIDIAN_EXPERT_LLM_BACKEND=fake`
- deterministic LLM responses are used for triage/review/family generation
- integration tests seed fixture `meridian` + `meridian_aux` trees instead of requiring real siblings

This keeps tests and demos offline-capable by default while preserving runtime compatibility with real local repos.

## CLI examples

Health + repo readiness:

```bash
meridian-expert doctor
```

Inspect triage + evidence summary:

```bash
meridian-expert task show <task_id> --evidence-summary
```

Compatibility risk check from changed files:

```bash
meridian-expert compat check --changed-file meridian/model/model.py --changed-file meridian/analysis/analyzer.py --markdown-report
```

Bundle exploration:

```bash
meridian-expert bundle list
meridian-expert bundle show meridian_analyzer_core
```

Learning/exemplar flows (non-prototype only):

```bash
meridian-expert learning list --status pending
meridian-expert exemplar list --status pending
```

## Review flow and prototype behavior

Prototype mode is currently the default for all task families (`config/lifecycle_modes.yaml`). Prototype artifacts use explicit suffixes and delivery paths under `deliveries/prototype/`.

Prototype deliveries are intentionally excluded from learning/exemplar nomination. Review approval is required before delivery in prototype mode.

## Builder status

Builder prompts/config entries exist as scaffolding, but builder routing is disabled by default (`builder_enabled: false`) and explicit builder routing is rejected unless enabled.

## Documentation and demos

- `docs/architecture.md`
- `docs/workspace-and-paths.md`
- `docs/runtime-taxonomy.md`
- `docs/task-lifecycle.md`
- `docs/bundles-and-compatibility.md`
- `docs/model-routing-and-openai.md`
- `docs/cli-guide.md`
- `docs/review-learning-and-exemplars.md`
- `docs/demos-and-notebooks.md`

Interactive walkthrough notebooks are in `demo/`.
