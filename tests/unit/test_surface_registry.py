from meridian_expert.investigation.surface_registry import SurfaceDependencyRegistry


def test_surface_dependency_registry_parsing() -> None:
    reg = SurfaceDependencyRegistry()
    rules = reg.list()

    assert rules
    assert any(
        rule["aux_file"] == "src/meridian_aux/predict/predict.py" for rule in rules
    )


def test_surface_dependency_lookup_by_file_path() -> None:
    reg = SurfaceDependencyRegistry()

    rule = reg.by_file_path("src/meridian_aux/contribution/control_contribution.py")
    assert rule is not None
    assert rule["cross_repo_route"] == "analyzer_based_aux"
    assert rule["dependency_mode"] == "compat_shim"
    assert rule["compat_shim"] is True


def test_surface_registry_route_and_mode_queries() -> None:
    reg = SurfaceDependencyRegistry()

    tier_1_rules = reg.by_hotspot_tier("tier_1")
    assert any(rule["aux_file"] == "src/meridian_aux/nest/nest.py" for rule in tier_1_rules)

    analyzer_rules = reg.by_cross_repo_route("analyzer_based_aux")
    assert any(
        rule["aux_file"] == "src/meridian_aux/dashboard/nordic_client.py"
        for rule in analyzer_rules
    )

    schema_mode_rules = reg.by_dependency_mode("schema_convention")
    assert any(rule["aux_file"] == "src/meridian_aux/charts/coefficients.py" for rule in schema_mode_rules)
