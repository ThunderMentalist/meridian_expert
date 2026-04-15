from __future__ import annotations

from meridian_expert.models.compatibility import CompatibilityReport


def generate_answer(goal: str, report: CompatibilityReport | None = None, *, include_plan: bool = False) -> str:
    lines = [f"Change summary for: {goal}", "", "Impact/risk assessment:"]

    if report and report.impacts:
        for impact in report.impacts:
            lines.append(f"- {impact.dependent_path} <- {impact.upstream_path}: {impact.risk_level}")
    else:
        lines.append("- No mapped impacts found from current changed surfaces.")

    if report and report.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend([f"- {warning}" for warning in report.warnings])

    if include_plan:
        lines.append("")
        lines.append("Update plan requested explicitly; drafting next steps is enabled.")

    return "\n".join(lines)
