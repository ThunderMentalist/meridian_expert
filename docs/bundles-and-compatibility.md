# Bundles and compatibility

## Ranked Meridian bundles

Bundle registry entries are ranked by `priority_rank` and weighted by task family + package domain. High-priority bundles include:

- `meridian_model_facade_lifecycle` (anchor: `meridian/model/model.py`)
- `meridian_model_math_core` (anchors include `adstock_hill.py`, `transformers.py`, `equations.py`)
- `meridian_analyzer_core` (anchor: `meridian/analysis/analyzer.py`)

Important path corrections are encoded:

- EDA is `meridian/model/eda/` (not `meridian/eda/`)
- scenario planner is top-level `scenarioplanner/` (not `meridian/scenario_planner/`)

## Aux hotspot tiers

Aux-focused bundles and surface rules classify risk by hotspot tier:

- **Tier 1**: highest sensitivity, includes
  - `src/meridian_aux/contribution/control_contribution.py`
  - `src/meridian_aux/predict/predict.py`
  - `src/meridian_aux/charts/transformed.py`
  - `src/meridian_aux/diagnostics/multicollinearity.py`
  - `src/meridian_aux/dashboard/nordic_client.py`
  - `src/meridian_aux/nest/nest.py`
- Tier 2/Tier 3: lower relative coupling risk

`nest/nest.py` is explicitly tracked as meaningfully coupled and under-tested.

## Dependency modes preserved

The system preserves these dependency modes:

- `public_api`
- `publicish_output`
- `semi_internal`
- `compat_shim`
- `schema_convention`
- `duck_typed`

These modes influence compatibility risk scoring and investigation expansion strategy.

## Compatibility manifest logic

`compat check` loads relationship mappings from `config/compatibility_manifest.yaml` and produces:

- changed upstream surfaces
- impacted `meridian_aux` dependents
- risk levels (including very-high paths for model reconstruction behavior)
- warnings (packaging mismatch, under-tested modules)
- known breakage patterns and supporting tests

Special handling includes an explicit warning when `src/meridian_aux/nest/nest.py` is changed.

## Packaging mismatch note (`meridian_aux`)

Documented compatibility warning:

- `meridian_aux` imports Meridian heavily
- but `meridian_aux` does **not** explicitly declare `google-meridian` in `pyproject.toml`

This is tracked as a packaging warning in the compatibility manifest.

## Compatibility shims and semi-internal paths

Known compatibility shims:

- `src/meridian_aux/contribution/control_contribution.py`
- `src/meridian_aux/dashboard/nordic_client.py`

Semi-internal/reconstruction-sensitive files include:

- `src/meridian_aux/predict/predict.py`
- `src/meridian_aux/charts/transformed.py`
- `src/meridian_aux/diagnostics/multicollinearity.py`

These surfaces are modeled as high/very-high risk when upstream model/analyzer contracts drift.
