from meridian_expert.investigation.compatibility_checker import CompatibilityChecker


def _impact(report, dependent_path: str):
    for impact in report.impacts:
        if impact.dependent_path == dependent_path:
            return impact
    return None


def test_analyzer_change_impacts_control_contribution_high_risk() -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths(["meridian/analysis/analyzer.py"])

    impact = _impact(report, "src/meridian_aux/contribution/control_contribution.py")
    assert impact is not None
    assert impact.risk_level == "high"


def test_analyzer_change_impacts_roi_medium_risk() -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths(["meridian/analysis/analyzer.py"])

    impact = _impact(report, "src/meridian_aux/optimization/roi.py")
    assert impact is not None
    assert impact.risk_level == "medium"


def test_model_change_impacts_predict_very_high_risk() -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths(["meridian/model/model.py"])

    impact = _impact(report, "src/meridian_aux/predict/predict.py")
    assert impact is not None
    assert impact.risk_level == "very_high"


def test_adstock_hill_change_impacts_transformed_or_multicollinearity_high_risk() -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths(["meridian/model/adstock_hill.py"])

    transformed = _impact(report, "src/meridian_aux/charts/transformed.py")
    multicollinearity = _impact(report, "src/meridian_aux/diagnostics/multicollinearity.py")

    assert transformed is not None
    assert multicollinearity is not None
    assert transformed.risk_level in {"high", "very_high"}
    assert multicollinearity.risk_level in {"high", "very_high"}


def test_under_tested_nest_warning_appears() -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths(["src/meridian_aux/nest/nest.py"])

    assert any("under-tested" in warning for warning in report.warnings)


def test_packaging_mismatch_warning_appears() -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths([])

    assert any("does not explicitly declare google-meridian" in warning for warning in report.warnings)


def test_markdown_report_rendering() -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths(["meridian/analysis/analyzer.py"])

    markdown = checker.render_markdown(report)
    assert "# Compatibility and update-risk report" in markdown
    assert "Changed surfaces" in markdown
    assert "src/meridian_aux/contribution/control_contribution.py" in markdown
    assert "Warnings" in markdown
