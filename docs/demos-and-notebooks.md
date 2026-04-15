# Demos and notebooks

The `demo/` directory contains notebook walkthroughs plus task markdown fixtures for repeatable prototype exercises.

## Notebook overview

- `demo/01_workspace_setup.ipynb`
  - demonstrates workspace/repository path configuration and environment bootstrap
- `demo/02_theory_task_walkthrough.ipynb`
  - demonstrates an anchor-first theory workflow
- `demo/03_usage_task_walkthrough.ipynb`
  - demonstrates usage-family execution with evidence and delivery gating
- `demo/04_update_risk_walkthrough.ipynb`
  - demonstrates update-impact/compatibility checks and hotspot-aware reasoning
- `demo/05_review_learning_and_follow_on.ipynb`
  - demonstrates review decisions, delivery gating, and follow-on task flow

## Task fixtures

`demo/tasks/` contains reusable task prompts such as:

- theory tasks (`theory_adstock`, `theory_analyzer_response_curves`)
- usage tasks (`usage_change_prior`, `usage_existing_object_snippet`)
- update-risk tasks (`update_analyzer_impact`)
- clarification scenarios (`clarification_ambiguous_scope`)

These are intended for deterministic, offline-capable demonstrations.

## Fixture-repo demo path

In Codex/CI-style environments, demos should use:

- synthetic fixture repos for Meridian and `meridian_aux`
- deterministic fake LLM backend (`MERIDIAN_EXPERT_LLM_BACKEND=fake`)

This validates cross-repo routing behavior without requiring access to real sibling repositories.

## Runtime reality

For human-run local environments, the same workflows are intended to run against real local sibling directories (`../meridian`, `../meridian_aux`) when available.

## Builder note

Builder workflows are currently scaffolded but disabled by default; notebooks should focus on theory/usage/updates prototype tracks unless builder enablement is explicitly added later.
