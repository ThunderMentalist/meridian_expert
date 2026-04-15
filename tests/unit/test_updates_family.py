from meridian_expert.models.compatibility import CompatibilityImpact, CompatibilityReport
from meridian_expert.task_families.updates import generate_answer


def test_updates_family_defaults_to_summary_and_risk_not_plan() -> None:
    report = CompatibilityReport(
        impacts=[
            CompatibilityImpact(
                upstream_path="meridian/model/model.py",
                dependent_path="src/meridian_aux/predict/predict.py",
                dependency_mode="semi_internal",
                hotspot_tier="tier_1",
                risk_level="very_high",
                reasons=["test reason"],
            )
        ]
    )

    text = generate_answer("Assess update risk", report)

    assert "Change summary for" in text
    assert "Impact/risk assessment" in text
    assert "Update plan requested explicitly" not in text


def test_updates_family_plan_only_when_requested() -> None:
    text = generate_answer("Assess update risk", report=None, include_plan=True)
    assert "Update plan requested explicitly" in text
