from pathlib import Path

from meridian_expert.investigation.repo_graph import build_import_graph, resolve_import_to_path
from meridian_expert.testing_support.repo_fixtures import build_fixture_workspace


def test_import_resolution_meridian_and_aux(tmp_path: Path) -> None:
    workspace = build_fixture_workspace(tmp_path)
    meridian_root = workspace["meridian"]
    aux_root = workspace["meridian_aux"]

    meridian_paths = {
        path.relative_to(meridian_root).as_posix() for path in meridian_root.rglob("*.py")
    }
    aux_paths = {path.relative_to(aux_root).as_posix() for path in aux_root.rglob("*.py")}

    assert (
        resolve_import_to_path("meridian.analysis.analyzer", "meridian", meridian_paths)
        == "meridian/analysis/analyzer.py"
    )
    assert (
        resolve_import_to_path("meridian.model.eda.eda_engine", "meridian", meridian_paths)
        == "meridian/model/eda/eda_engine.py"
    )
    assert resolve_import_to_path("schema", "meridian", meridian_paths) == "schema.py"
    assert (
        resolve_import_to_path("scenarioplanner.mmm_ui_proto_generator", "meridian", meridian_paths)
        == "scenarioplanner/mmm_ui_proto_generator.py"
    )

    assert (
        resolve_import_to_path("meridian_aux.dashboard.nordic_client", "meridian_aux", aux_paths)
        == "src/meridian_aux/dashboard/nordic_client.py"
    )
    assert (
        resolve_import_to_path("meridian_aux.predict.predict", "meridian_aux", aux_paths)
        == "src/meridian_aux/predict/predict.py"
    )


def test_direct_dependencies_for_key_files(tmp_path: Path) -> None:
    workspace = build_fixture_workspace(tmp_path)
    meridian_graph = build_import_graph(workspace["meridian"], repo_kind="meridian")
    aux_graph = build_import_graph(workspace["meridian_aux"], repo_kind="meridian_aux")

    model_deps = meridian_graph.get_direct_dependencies("meridian/model/model.py")
    assert "meridian/model/equations.py" in model_deps
    assert "meridian/model/adstock_hill.py" in model_deps
    assert "meridian/model/transformers.py" in model_deps
    assert "meridian/data/input_data.py" in model_deps

    analyzer_deps = meridian_graph.get_direct_dependencies("meridian/analysis/analyzer.py")
    assert "meridian/model/model.py" in analyzer_deps
    assert "meridian/analysis/visualizer.py" in analyzer_deps

    control_deps = aux_graph.get_direct_dependencies(
        "src/meridian_aux/contribution/control_contribution.py"
    )
    assert "src/meridian_aux/dashboard/nordic_client.py" in control_deps

    predict_deps = aux_graph.get_direct_dependencies("src/meridian_aux/predict/predict.py")
    assert "src/meridian_aux/contribution/control_contribution.py" in predict_deps


def test_reverse_dependencies_and_special_paths(tmp_path: Path) -> None:
    workspace = build_fixture_workspace(tmp_path)
    meridian_graph = build_import_graph(workspace["meridian"], repo_kind="meridian")

    reverse_model = meridian_graph.get_reverse_dependencies("meridian/model/model.py")
    assert "meridian/analysis/analyzer.py" in reverse_model
    assert "meridian/model/posterior_sampler.py" in reverse_model
    assert "meridian/backend/__init__.py" in reverse_model

    reverse_schema = meridian_graph.get_reverse_dependencies("schema.py")
    assert reverse_schema == set()

    scenarioplanner_deps = meridian_graph.get_direct_dependencies(
        "scenarioplanner/mmm_ui_proto_generator.py"
    )
    assert "meridian/analysis/analyzer.py" in scenarioplanner_deps
