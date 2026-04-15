from pathlib import Path

from meridian_expert.investigation.bundle_registry import BundleRegistry
from meridian_expert.investigation.evidence_builder import (
    MAX_ANCHORS,
    MAX_PROMOTED,
    MAX_SUPPORT,
    MAX_TESTS,
    build_evidence_pack,
    build_investigation_plan,
)
from meridian_expert.investigation.repo_graph import build_import_graph
from meridian_expert.investigation.surface_registry import SurfaceDependencyRegistry
from meridian_expert.models.task import TaskBrief
from meridian_expert.testing_support.repo_fixtures import build_fixture_workspace


def _build_graphs(tmp_path: Path) -> dict:
    workspace = build_fixture_workspace(tmp_path)
    return {
        "meridian": build_import_graph(workspace["meridian"], repo_kind="meridian"),
        "meridian_aux": build_import_graph(workspace["meridian_aux"], repo_kind="meridian_aux"),
    }


def _brief(title: str, goal: str, family: str = "theory", domain: str = "model") -> TaskBrief:
    return TaskBrief(
        title=title,
        task_family=family,
        goal=goal,
        package_domain=domain,
    )


def test_anchor_first_plan_for_model_py(tmp_path: Path) -> None:
    plan = build_investigation_plan(
        brief=_brief("Model question", "Deep dive into meridian/model/model.py behavior."),
        bundle_registry=BundleRegistry(),
        surface_registry=SurfaceDependencyRegistry(),
        graphs=_build_graphs(tmp_path),
        triage_candidate_anchors=["meridian/model/model.py"],
    )

    assert plan.anchor_files == ["meridian/model/model.py"]
    assert "meridian/model/adstock_hill.py" in plan.mandatory_expansions
    assert "meridian/data/input_data.py" in plan.mandatory_expansions
    assert "meridian/model/model_test.py" in plan.selected_tests


def test_anchor_first_plan_for_analyzer_py(tmp_path: Path) -> None:
    plan = build_investigation_plan(
        brief=_brief("Analyzer question", "How analyzer consumes model internals?", family="usage", domain="analysis"),
        bundle_registry=BundleRegistry(),
        surface_registry=SurfaceDependencyRegistry(),
        graphs=_build_graphs(tmp_path),
        triage_candidate_anchors=["meridian/analysis/analyzer.py"],
    )

    assert plan.anchor_files == ["meridian/analysis/analyzer.py"]
    assert "meridian/model/model.py" in plan.mandatory_expansions
    assert "meridian/model/transformers.py" in plan.mandatory_expansions
    assert "meridian/analysis/analyzer_test.py" in plan.selected_tests


def test_aux_route_recipe_for_control_contribution(tmp_path: Path) -> None:
    plan = build_investigation_plan(
        brief=_brief("Control contribution", "Investigate src/meridian_aux/contribution/control_contribution.py"),
        bundle_registry=BundleRegistry(),
        surface_registry=SurfaceDependencyRegistry(),
        graphs=_build_graphs(tmp_path),
    )
    assert plan.anchor_files == ["src/meridian_aux/contribution/control_contribution.py"]
    assert plan.cross_repo_route == "analyzer_based_aux"
    assert plan.dependency_mode == "compat_shim"
    assert plan.hotspot_tier == "tier_1"
    assert "meridian/analysis/analyzer.py" in plan.mandatory_expansions
    assert "tests/test_contribution_control_contribution.py" in plan.selected_tests


def test_aux_route_recipe_for_predict(tmp_path: Path) -> None:
    plan = build_investigation_plan(
        brief=_brief("Predict route", "Need details on src/meridian_aux/predict/predict.py"),
        bundle_registry=BundleRegistry(),
        surface_registry=SurfaceDependencyRegistry(),
        graphs=_build_graphs(tmp_path),
    )
    assert plan.anchor_files == ["src/meridian_aux/predict/predict.py"]
    assert plan.cross_repo_route == "model_object_based_aux"
    assert plan.dependency_mode == "semi_internal"
    assert "meridian/model/model.py" in plan.mandatory_expansions
    assert "tests/test_predict_predict.py" in plan.selected_tests

    pack = build_evidence_pack(plan, _build_graphs(tmp_path), SurfaceDependencyRegistry())
    assert any(item.reconstructs_meridian_behavior for item in pack.items)


def test_aux_route_recipe_for_dashboard_nordic_client(tmp_path: Path) -> None:
    plan = build_investigation_plan(
        brief=_brief("Nordic client", "Check src/meridian_aux/dashboard/nordic_client.py compatibility"),
        bundle_registry=BundleRegistry(),
        surface_registry=SurfaceDependencyRegistry(),
        graphs=_build_graphs(tmp_path),
    )
    assert plan.anchor_files == ["src/meridian_aux/dashboard/nordic_client.py"]
    assert plan.dependency_mode == "compat_shim"
    assert "meridian/analysis/analyzer.py" in plan.mandatory_expansions
    assert "src/meridian_aux/contribution/control_contribution.py" in plan.mandatory_expansions


def test_under_tested_flag_for_nest(tmp_path: Path) -> None:
    plan = build_investigation_plan(
        brief=_brief("Nest bridge", "Evaluate src/meridian_aux/nest/nest.py"),
        bundle_registry=BundleRegistry(),
        surface_registry=SurfaceDependencyRegistry(),
        graphs=_build_graphs(tmp_path),
    )

    assert plan.under_tested is True
    assert any("TODO placeholder" in r for r in plan.rationale)

    pack = build_evidence_pack(plan, _build_graphs(tmp_path), SurfaceDependencyRegistry())
    assert any("Under-tested route" in note for note in pack.notes)


def test_bounded_stop_rule(tmp_path: Path) -> None:
    plan = build_investigation_plan(
        brief=_brief("Bounded expansion", "Investigate meridian/model/model.py and analyzer."),
        bundle_registry=BundleRegistry(),
        surface_registry=SurfaceDependencyRegistry(),
        graphs=_build_graphs(tmp_path),
        triage_candidate_anchors=["meridian/model/model.py", "meridian/analysis/analyzer.py", "meridian/data/input_data.py"],
    )

    assert len(plan.anchor_files) <= MAX_ANCHORS
    assert len(plan.selected_tests) <= MAX_TESTS
    assert len(plan.support_files) <= MAX_SUPPORT

    pack = build_evidence_pack(plan, _build_graphs(tmp_path), SurfaceDependencyRegistry())
    promoted_non_core = [
        item.path
        for item in pack.items
        if item.path not in set(plan.anchor_files + plan.mandatory_expansions + plan.selected_tests + plan.support_files)
    ]
    assert len(promoted_non_core) <= MAX_PROMOTED
