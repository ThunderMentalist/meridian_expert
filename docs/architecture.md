# Architecture

## System shape

`meridian_expert` is organized as a CLI-first orchestration layer with shared infrastructure plus task-family-specific generation logic.

### Shared infrastructure

Core shared modules handle:

- path and workspace resolution
- task/cycle IDs
- SQLite task, artifact, review, and nomination persistence
- lifecycle orchestration and state transitions
- review queue and gating
- bundle + surface registries
- compatibility impact checking
- model profile loading + backend routing (OpenAI or deterministic fake)

### Task families

Task families are:

- `theory`
- `usage`
- `updates`
- `builder` (scaffolded, disabled by default)

Routing keeps builder disabled unless explicitly enabled. If triage resolves to builder while disabled, routing falls back to theory.

## Anchor-first investigation

Investigation begins from ranked anchor files (from bundle and surface registries), then expands outward by explicit cross-repo route rules and mandatory expansions. This is critical for Meridian because:

- `meridian/model/model.py` is a façade/orchestrator, not the full theoretical implementation
- `meridian/analysis/analyzer.py` is a major downstream consumer of model internals
- `meridian/analysis/optimizer.py` is downstream of analyzer + model internals

So, anchor files are the starting map, not the full truth surface.

## Bundles are maps, not walls

Bundle registry entries provide:

- priority rank and task/domain weights
- anchor files and primary files
- neighboring bundles and expansion hints
- test references and hotspot/dependency defaults

The orchestration selects top-ranked bundles and emits evidence from those surfaces. Analysts should expand evidence across adjacent bundles when dependency routes indicate coupled behavior.

## Surface dependency registry

The surface registry models known Meridian↔`meridian_aux` coupling for high-sensitivity aux files. It captures:

- cross-repo route (`analyzer_based_aux`, `model_object_based_aux`, etc.)
- dependency mode (`public_api`, `publicish_output`, `semi_internal`, `compat_shim`, `schema_convention`, `duck_typed`)
- hotspot tier
- compatibility shim and under-tested flags
- mandatory Meridian expansions and known breakage patterns

This gives a structured, explicit contract for cross-repo triage and update risk reasoning.

## Why `model.py` and `analyzer.py` are treated as orchestrators

Meridian coupling patterns require special treatment:

- `meridian/model/model.py` coordinates model object lifecycle and routes into transform/equation internals.
- `meridian/analysis/analyzer.py` consumes model internals and shapes outputs used by multiple aux surfaces.

Therefore, update analysis cannot treat either file as isolated. Investigation plans should attach supporting files (`adstock_hill.py`, `transformers.py`, `equations.py`, `input_data.py`, `visualizer.py`) according to the route and dependency mode in play.
