from pathlib import Path

import yaml

from meridian_expert.orchestration.triage import deterministic_triage_from_text


REQUIRED_CASES = {
    "model_theory_model_py",
    "analyzer_usage_response_curves",
    "usage_predict_py",
    "update_control_contribution",
    "update_dashboard_nordic_client",
    "update_under_tested_nest",
    "clarification_required",
    "follow_on_task_case",
    "prototype_isolation_case",
}


def test_required_golden_cases_exist() -> None:
    base = Path("tests/golden_tasks/cases")
    present = {p.name for p in base.iterdir() if p.is_dir()}
    assert REQUIRED_CASES.issubset(present)


def test_golden_case_structural_expectations() -> None:
    base = Path("tests/golden_tasks/cases")

    for case in sorted(REQUIRED_CASES):
        case_dir = base / case
        task_text = (case_dir / "task.md").read_text().strip()
        expected = yaml.safe_load((case_dir / "expected.yaml").read_text())

        brief = deterministic_triage_from_text(task_text)

        assert brief.task_family.value == expected["expected_family"]
        assert brief.needs_clarification == expected.get("expects_clarification", False)

        expected_route = expected.get("expected_route")
        if expected_route:
            assert brief.cross_repo_route == expected_route

        for expected_anchor in expected.get("expected_anchors", []):
            assert expected_anchor in brief.candidate_anchor_files

        if "expects_under_tested" in expected:
            assert brief.under_tested_risk == expected["expects_under_tested"]
