from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from meridian_expert.investigation.bundle_registry import BundleRegistry
from meridian_expert.investigation.repo_graph import ImportGraph
from meridian_expert.investigation.surface_registry import SurfaceDependencyRegistry
from meridian_expert.models.evidence import EvidenceItem, EvidencePack, InvestigationPlan
from meridian_expert.models.task import TaskBrief

MAX_ANCHORS = 2
MAX_PROMOTED = 6
MAX_TESTS = 6
MAX_SUPPORT = 6

MANDATORY_EXPANSIONS_BY_ANCHOR: dict[str, list[str]] = {
    "meridian/model/model.py": [
        "meridian/model/adstock_hill.py",
        "meridian/model/equations.py",
        "meridian/model/transformers.py",
        "meridian/model/context.py",
        "meridian/model/spec.py",
        "meridian/model/prior_distribution.py",
        "meridian/model/prior_sampler.py",
        "meridian/model/posterior_sampler.py",
        "meridian/model/media.py",
        "meridian/model/knots.py",
        "meridian/data/input_data.py",
        "meridian/data/time_coordinates.py",
    ],
    "meridian/analysis/analyzer.py": [
        "meridian/model/model.py",
        "meridian/model/context.py",
        "meridian/model/equations.py",
        "meridian/model/adstock_hill.py",
        "meridian/model/transformers.py",
    ],
}

MANDATORY_TESTS_BY_ANCHOR: dict[str, list[str]] = {
    "meridian/model/model.py": [
        "meridian/model/model_test.py",
        "meridian/model/adstock_hill_test.py",
        "meridian/model/equations_test.py",
        "meridian/model/transformers_test.py",
        "meridian/model/context_test.py",
        "meridian/model/prior_distribution_test.py",
    ],
    "meridian/analysis/analyzer.py": ["meridian/analysis/analyzer_test.py"],
}


@dataclass(frozen=True)
class AuxRouteRecipe:
    anchor: str
    route: str
    mandatory_expansions: list[str]
    selected_tests: list[str]
    dependency_mode: str
    hotspot_tier: str | None = None
    under_tested: bool = False
    reconstructs_meridian_behavior: bool = False
    note: str | None = None


AUX_ROUTE_RECIPES: dict[str, AuxRouteRecipe] = {
    "src/meridian_aux/contribution/control_contribution.py": AuxRouteRecipe(
        anchor="src/meridian_aux/contribution/control_contribution.py",
        route="analyzer_based_aux",
        mandatory_expansions=[
            "meridian/analysis/analyzer.py",
            "meridian/model/model.py",
            "meridian/model/context.py",
        ],
        selected_tests=["tests/test_contribution_control_contribution.py"],
        dependency_mode="compat_shim",
        hotspot_tier="tier_1",
    ),
    "src/meridian_aux/predict/predict.py": AuxRouteRecipe(
        anchor="src/meridian_aux/predict/predict.py",
        route="model_object_based_aux",
        mandatory_expansions=[
            "meridian/model/model.py",
            "meridian/model/equations.py",
            "meridian/model/adstock_hill.py",
            "meridian/model/transformers.py",
            "meridian/data/input_data.py",
        ],
        selected_tests=["tests/test_predict_predict.py"],
        dependency_mode="semi_internal",
        hotspot_tier="tier_1",
        reconstructs_meridian_behavior=True,
    ),
    "src/meridian_aux/charts/transformed.py": AuxRouteRecipe(
        anchor="src/meridian_aux/charts/transformed.py",
        route="model_object_based_aux",
        mandatory_expansions=[
            "meridian/model/model.py",
            "meridian/model/transformers.py",
            "meridian/model/adstock_hill.py",
            "meridian/model/equations.py",
        ],
        selected_tests=["tests/test_charts_transformed.py"],
        dependency_mode="semi_internal",
        reconstructs_meridian_behavior=True,
    ),
    "src/meridian_aux/dashboard/nordic_client.py": AuxRouteRecipe(
        anchor="src/meridian_aux/dashboard/nordic_client.py",
        route="analyzer_based_aux",
        mandatory_expansions=[
            "meridian/analysis/analyzer.py",
            "src/meridian_aux/contribution/control_contribution.py",
        ],
        selected_tests=["tests/test_dashboard_nordic_client.py"],
        dependency_mode="compat_shim",
        hotspot_tier="tier_1",
    ),
    "src/meridian_aux/nest/nest.py": AuxRouteRecipe(
        anchor="src/meridian_aux/nest/nest.py",
        route="decomposition_bridge_aux",
        mandatory_expansions=[
            "meridian/analysis/visualizer.py",
            "meridian/analysis/analyzer.py",
        ],
        selected_tests=["tests/test_nest_nest.py"],
        dependency_mode="publicish_output",
        hotspot_tier="tier_1",
        under_tested=True,
        note="Real test coverage is effectively absent because test_nest_nest.py is only a TODO placeholder.",
    ),
    "src/meridian_aux/diagnostics/multicollinearity.py": AuxRouteRecipe(
        anchor="src/meridian_aux/diagnostics/multicollinearity.py",
        route="model_object_based_aux",
        mandatory_expansions=[
            "meridian/model/model.py",
            "meridian/model/adstock_hill.py",
            "meridian/model/transformers.py",
        ],
        selected_tests=["tests/test_diagnostics_multicollinearity.py"],
        dependency_mode="semi_internal",
        hotspot_tier="tier_1",
    ),
}


def _dedupe_keep_order(values: list[str], limit: int | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        out.append(value)
        seen.add(value)
        if limit is not None and len(out) >= limit:
            break
    return out


def _repo_for_path(path: str) -> str:
    return "meridian_aux" if path.startswith("src/meridian_aux/") or path.startswith("tests/") else "meridian"


def _infer_surface_rule(brief: TaskBrief, surface_registry: SurfaceDependencyRegistry) -> dict | None:
    all_rules = surface_registry.list()
    haystack = " ".join([brief.title, brief.goal, *brief.constraints, *brief.unknowns]).lower()
    for rule in all_rules:
        aux_file = rule["aux_file"]
        basename = aux_file.rsplit("/", 1)[-1]
        if aux_file.lower() in haystack or basename.lower() in haystack:
            return rule
    return None


def _select_anchor_files(
    brief: TaskBrief,
    bundle_registry: BundleRegistry,
    surface_registry: SurfaceDependencyRegistry,
    triage_candidate_anchors: list[str] | None,
) -> tuple[list[str], list[str], dict | None]:
    rationale: list[str] = []
    surface_rule = _infer_surface_rule(brief, surface_registry)

    if triage_candidate_anchors:
        anchors = _dedupe_keep_order(triage_candidate_anchors, limit=MAX_ANCHORS)
        rationale.append("Selected explicit triage candidate anchors.")
        return anchors, rationale, surface_rule

    if surface_rule:
        recipe = AUX_ROUTE_RECIPES.get(surface_rule["aux_file"])
        if recipe:
            anchors = [recipe.anchor]
            rationale.append(f"Selected aux route recipe anchor: {recipe.route}.")
            return anchors, rationale, surface_rule

        anchors = _dedupe_keep_order(surface_rule["meridian_anchor_files"], limit=MAX_ANCHORS)
        rationale.append("Selected anchors from surface dependency registry rule.")
        return anchors, rationale, surface_rule

    ranked = bundle_registry.rank_for(brief.task_family.value, brief.package_domain)
    if not ranked:
        ranked = bundle_registry.list()
    top = ranked[0]
    anchors = _dedupe_keep_order(top["anchor_files"], limit=MAX_ANCHORS)
    rationale.append(f"Selected highest-ranked bundle anchors from {top['name']}.")
    return anchors, rationale, surface_rule


def _collect_direct_imports(anchor_files: list[str], graphs: dict[str, ImportGraph]) -> list[str]:
    direct: list[str] = []
    for anchor in anchor_files:
        repo = _repo_for_path(anchor)
        graph = graphs.get(repo)
        if not graph:
            continue
        direct.extend(sorted(graph.get_direct_dependencies(anchor)))
    return _dedupe_keep_order(direct)


def _promote_neighboring_bundle_files(
    imports: list[str],
    bundle_registry: BundleRegistry,
    excluded: set[str],
) -> tuple[list[str], list[str], list[str]]:
    promoted: list[str] = []
    selected_bundles: list[str] = []
    rationale: list[str] = []
    for path in imports:
        home_bundle = bundle_registry.home_bundle_for_file(path)
        if not home_bundle:
            continue
        selected_bundles.append(home_bundle["name"])
        candidates = [*home_bundle["anchor_files"], *home_bundle["primary_files"]]
        for candidate in candidates:
            if candidate in excluded or candidate in promoted:
                continue
            promoted.append(candidate)
            if len(promoted) >= MAX_PROMOTED:
                break
        rationale.append(f"Promoted files from neighboring bundle {home_bundle['name']} via import {path}.")
        if len(promoted) >= MAX_PROMOTED:
            break

    return promoted, _dedupe_keep_order(selected_bundles), _dedupe_keep_order(rationale)


def _derive_tests_for_paths(paths: list[str]) -> list[str]:
    tests: list[str] = []
    for path in paths:
        if path.startswith("meridian/") and path.endswith(".py"):
            tests.append(path.removesuffix(".py") + "_test.py")
        if path.startswith("src/meridian_aux/") and path.endswith(".py"):
            leaf = path.removeprefix("src/meridian_aux/").removesuffix(".py").replace("/", "_")
            tests.append(f"tests/test_{leaf}.py")
    return tests


def _support_files_for_context(plan_paths: list[str], selected_bundles: list[str], bundle_registry: BundleRegistry) -> list[str]:
    support: list[str] = []
    if any("meridian/model/" in path for path in plan_paths):
        support.append("meridian/constants.py")
    if any("analyzer.py" in path or "visualizer.py" in path for path in plan_paths):
        support.append("meridian/templates/formatter.py")
        support.append("meridian/backend/__init__.py")
    if any(path.startswith("meridian/schema/") for path in plan_paths):
        support.append("schema.py")

    for name in selected_bundles:
        bundle = bundle_registry.by_name(name)
        if bundle:
            support.extend(bundle.get("optional_support_files", []))

    return _dedupe_keep_order(support, limit=MAX_SUPPORT)


def build_investigation_plan(
    brief: TaskBrief,
    bundle_registry: BundleRegistry,
    surface_registry: SurfaceDependencyRegistry,
    graphs: dict[str, ImportGraph],
    triage_candidate_anchors: list[str] | None = None,
) -> InvestigationPlan:
    anchor_files, rationale, surface_rule = _select_anchor_files(
        brief=brief,
        bundle_registry=bundle_registry,
        surface_registry=surface_registry,
        triage_candidate_anchors=triage_candidate_anchors,
    )

    mandatory_expansions: list[str] = []
    selected_tests: list[str] = []
    selected_bundles: list[str] = []
    cross_repo_route: str | None = None
    hotspot_tier: str | None = None
    dependency_mode: str | None = None
    under_tested = False

    recipe: AuxRouteRecipe | None = None
    if surface_rule:
        recipe = AUX_ROUTE_RECIPES.get(surface_rule["aux_file"])

    if recipe:
        mandatory_expansions.extend(recipe.mandatory_expansions)
        selected_tests.extend(recipe.selected_tests)
        cross_repo_route = recipe.route
        hotspot_tier = recipe.hotspot_tier
        dependency_mode = recipe.dependency_mode
        under_tested = recipe.under_tested
        rationale.append("Added mandatory expansions and tests from explicit aux route recipe.")
    elif surface_rule:
        mandatory_expansions.extend(surface_rule["mandatory_meridian_expansions"])
        selected_tests.extend(surface_rule["supporting_tests"])
        cross_repo_route = surface_rule["cross_repo_route"]
        hotspot_tier = surface_rule["hotspot_tier"]
        dependency_mode = surface_rule["dependency_mode"]
        under_tested = surface_rule["under_tested"]
        rationale.append("Added mandatory expansions and tests from surface dependency registry.")

    for anchor in anchor_files:
        mandatory_expansions.extend(MANDATORY_EXPANSIONS_BY_ANCHOR.get(anchor, []))
        selected_tests.extend(MANDATORY_TESTS_BY_ANCHOR.get(anchor, []))

    direct_imports = _collect_direct_imports(anchor_files + mandatory_expansions, graphs)
    promoted, promoted_bundles, promote_rationale = _promote_neighboring_bundle_files(
        imports=direct_imports,
        bundle_registry=bundle_registry,
        excluded=set(anchor_files + mandatory_expansions),
    )
    rationale.extend(promote_rationale)

    selected_bundles.extend(promoted_bundles)
    for anchor in anchor_files:
        home = bundle_registry.home_bundle_for_file(anchor)
        if home:
            selected_bundles.append(home["name"])

    selected_tests.extend(_derive_tests_for_paths(anchor_files + mandatory_expansions + direct_imports))
    for bundle_name in _dedupe_keep_order(selected_bundles):
        bundle = bundle_registry.by_name(bundle_name)
        if bundle:
            selected_tests.extend(bundle.get("supporting_tests", []))

    all_primary = _dedupe_keep_order(anchor_files + mandatory_expansions + direct_imports + promoted)
    support_files = _support_files_for_context(all_primary, _dedupe_keep_order(selected_bundles), bundle_registry)

    plan = InvestigationPlan(
        anchor_files=_dedupe_keep_order(anchor_files, limit=MAX_ANCHORS),
        selected_bundles=_dedupe_keep_order(selected_bundles),
        mandatory_expansions=_dedupe_keep_order(mandatory_expansions),
        selected_tests=_dedupe_keep_order(selected_tests, limit=MAX_TESTS),
        support_files=support_files,
        rationale=_dedupe_keep_order(rationale),
        cross_repo_route=cross_repo_route,
        hotspot_tier=hotspot_tier,
        dependency_mode=dependency_mode,
        under_tested=under_tested,
    )

    if recipe and recipe.note:
        plan.rationale.append(recipe.note)

    return plan


def build_evidence_pack(
    plan: InvestigationPlan,
    graphs: dict[str, ImportGraph],
    surface_registry: SurfaceDependencyRegistry,
) -> EvidencePack:
    surface_rule = None
    for anchor in plan.anchor_files:
        if anchor.startswith("src/meridian_aux/"):
            surface_rule = surface_registry.by_file_path(anchor)
            break

    reconstructs = False
    schema_convention = False
    if surface_rule:
        recipe = AUX_ROUTE_RECIPES.get(surface_rule["aux_file"])
        reconstructs = recipe.reconstructs_meridian_behavior if recipe else False
        schema_convention = surface_rule["dependency_mode"] == "schema_convention"

    notes: list[str] = []
    if plan.dependency_mode == "compat_shim":
        notes.append("Compatibility shim dependency mode; signature drift risk is elevated.")
    if plan.under_tested:
        notes.append("Under-tested route; treat behavioral assumptions as provisional.")
    if reconstructs:
        notes.append("Route reconstructs Meridian behavior; include transform semantics checks.")

    items_by_path: OrderedDict[str, EvidenceItem] = OrderedDict()

    def put(path: str, rationale: str, authority_rank: int, significance: float, direct: bool, test_strength: str | None = None) -> None:
        if path in items_by_path:
            return
        items_by_path[path] = EvidenceItem(
            repo_name=_repo_for_path(path),
            path=path,
            rationale=rationale,
            authority_rank=authority_rank,
            significance=significance,
            direct=direct,
            dependency_mode=plan.dependency_mode,
            test_coverage_strength=test_strength,
            reconstructs_meridian_behavior=reconstructs,
            schema_convention_dependency=schema_convention,
        )

    for anchor in plan.anchor_files:
        put(anchor, "Anchor-first selection.", authority_rank=1, significance=1.0, direct=True)

    for path in plan.mandatory_expansions:
        put(path, "Mandatory expansion for dependency-aware context.", authority_rank=2, significance=0.9, direct=True)

    direct_deps = _collect_direct_imports(plan.anchor_files + plan.mandatory_expansions, graphs)
    for path in direct_deps:
        put(path, "Direct internal import expansion.", authority_rank=3, significance=0.75, direct=False)

    for test in plan.selected_tests:
        strength = "placeholder" if "test_nest_nest.py" in test and plan.under_tested else "targeted"
        put(test, "Selected validation evidence for anchor or expansion behavior.", authority_rank=2, significance=0.8, direct=True, test_strength=strength)

    for support in plan.support_files:
        put(support, "Support file for constants/templates/schema context.", authority_rank=4, significance=0.55, direct=False)

    return EvidencePack(anchor_files=plan.anchor_files, items=list(items_by_path.values()), notes=notes)


def render_evidence_bundle_markdown(plan: InvestigationPlan, pack: EvidencePack) -> str:
    lines = [
        "# Evidence Bundle",
        "",
        "## Selected Anchors",
        *[f"- `{path}`" for path in plan.anchor_files],
        "",
        "## Selected Bundles",
        *[f"- `{name}`" for name in plan.selected_bundles],
        "",
        "## Selected Tests",
        *[f"- `{path}`" for path in plan.selected_tests],
        "",
        "## Evidence Items",
    ]
    for item in pack.items:
        lines.append(
            f"- `{item.path}` | repo={item.repo_name} | rank={item.authority_rank} | direct={item.direct} | reason={item.rationale}"
        )

    lines.append("")
    lines.append("## Notes")
    for note in [*plan.rationale, *pack.notes]:
        lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


# Backward-compatible helper used by the current runner.
def from_bundle(bundle: dict) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            repo_name=_repo_for_path(path),
            path=path,
            rationale=f"Selected from bundle {bundle['name']}",
            authority_rank=3,
            significance=0.6,
            direct=True,
        )
        for path in bundle.get("files", [])
    ]
