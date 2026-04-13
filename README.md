# meridian_expert

`meridian_expert` is a CLI-first, local, review-gated expert system for working with two sibling repositories:

- `../meridian` (Google Meridian MMM)
- `../meridian_aux` (adjacent dependent repo)

It is designed for precise, auditable, human-supervised workflows across theory, usage, and update-impact tasks, with a scaffolded builder branch that is disabled by default.

## Install

```bash
python -m pip install -e .[dev]
```

## Workspace layout

```text
workspace/
  meridian/
  meridian_aux/
  meridian_expert/
```

Path resolution precedence:
1. CLI overrides
2. env vars (`MERIDIAN_REPO_PATH`, `MERIDIAN_AUX_REPO_PATH`, `MERIDIAN_EXPERT_WORKSPACE`)
3. `config/repos.local.yaml` (gitignored)
4. default sibling paths

## Environment

Copy `.env.example`, set `OPENAI_API_KEY`, and optionally set repository path overrides.

## Quickstart

```bash
meridian-expert doctor
meridian-expert task create demo/tasks/theory_adstock/task.md
meridian-expert task run T-20260413-0001 --to-gate
meridian-expert review queue
```

## Lifecycle and review

Task families run in lifecycle modes from `config/lifecycle_modes.yaml`. Prototype mode stores artifacts in a prototype namespace and blocks reuse. Delivery in prototype/warm-up requires review approval.

## Builder path

Builder commands and prompts are scaffolded, but hidden from default routing and disabled unless explicitly selected.

## Docs and demos

- `docs/` for architecture, lifecycle, bundles, compatibility, OpenAI model routing, CLI, and review/learning behavior.
- `demo/` includes executable notebooks and sample tasks.
