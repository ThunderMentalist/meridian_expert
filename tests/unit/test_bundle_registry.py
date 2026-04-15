from meridian_expert.investigation.bundle_registry import BundleRegistry


def test_bundle_registry_parsing_and_ranking() -> None:
    reg = BundleRegistry()
    bundles = reg.list()

    assert bundles
    ranks = [bundle["priority_rank"] for bundle in bundles]
    assert ranks == sorted(ranks)

    ranked = reg.rank_for("theory", "model")
    assert ranked
    assert ranked[0]["name"] == "meridian_model_facade_lifecycle"


def test_corrected_path_facts_for_eda_and_scenarioplanner() -> None:
    reg = BundleRegistry()

    eda_bundle = reg.by_name("meridian_eda_subsystem")
    assert eda_bundle is not None
    assert "meridian/model/eda/eda_engine.py" in eda_bundle["primary_files"]
    assert all(not path.startswith("meridian/eda") for path in eda_bundle["files"])

    scenario_bundle = reg.by_name("meridian_scenario_planner_support")
    assert scenario_bundle is not None
    assert "scenarioplanner/mmm_ui_proto_generator.py" in scenario_bundle["primary_files"]
    assert all("meridian/scenario_planner" not in path for path in scenario_bundle["files"])


def test_home_bundle_lookup_by_file_path() -> None:
    reg = BundleRegistry()

    home = reg.home_bundle_for_file("meridian/analysis/analyzer.py")
    assert home is not None
    assert home["name"] == "meridian_analyzer_core"


def test_notes_preserve_orchestrator_semantics() -> None:
    reg = BundleRegistry()

    model_bundle = reg.by_name("meridian_model_facade_lifecycle")
    analyzer_bundle = reg.by_name("meridian_analyzer_core")

    assert model_bundle is not None
    assert analyzer_bundle is not None
    assert "façade/orchestrator" in model_bundle["notes"]
    assert "downstream consumer" in analyzer_bundle["notes"]
