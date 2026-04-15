from __future__ import annotations

from meridian_expert.models.evidence import EvidencePack
from meridian_expert.orchestration.runner import DraftOutput

_AUX_CATEGORY_RULES: tuple[tuple[str, str], ...] = (
    ("src/meridian_aux/contribution/control_contribution.py", "compatibility shim"),
    ("src/meridian_aux/dashboard/nordic_client.py", "compatibility shim"),
    ("src/meridian_aux/predict/predict.py", "reconstruction of Meridian model behavior"),
    ("src/meridian_aux/charts/transformed.py", "reconstruction of Meridian model behavior"),
    ("src/meridian_aux/nest/nest.py", "visualizer / decomposition bridge"),
)


def _aux_category(path: str | None) -> str | None:
    if not path:
        return None
    for candidate, category in _AUX_CATEGORY_RULES:
        if path.endswith(candidate):
            return category
    if "/contribution/" in path or "/dashboard/" in path:
        return "wrapper over Analyzer output schema"
    if "/charts/" in path or "/predict/" in path:
        return "reconstruction of Meridian model behavior"
    if "/nest/" in path:
        return "visualizer / decomposition bridge"
    return "schema-convention or duck-typed consumer"


def _anchor_summary(target_path: str | None) -> list[str]:
    if not target_path:
        return []
    if target_path.endswith("meridian/model/model.py"):
        return [
            "`meridian/model/model.py` behaves as an orchestration façade; the underlying theory lives across transformation and equation layers.",
            "Interpret behavior by following analyzer and optimizer downstream surfaces instead of treating this file as a self-contained theory source.",
        ]
    if target_path.endswith("meridian/analysis/analyzer.py"):
        return [
            "`analyzer.py` is a downstream consumer of fitted model internals, not an isolated analysis utility.",
            "Conceptual explanations should tie Analyzer outputs back to model-side state and transforms.",
        ]
    return []


def generate_answer(
    goal: str,
    evidence_pack: EvidencePack | None = None,
    *,
    target_path: str | None = None,
    include_code_tour: bool = False,
) -> DraftOutput:
    """Generate conceptual-first theory output grounded in evidence."""

    lines: list[str] = [f"## Theory answer", "", f"### Conceptual explanation", f"{goal.strip()}."]

    lines.extend(["", "### Grounding from code evidence"])
    anchor_lines = _anchor_summary(target_path)
    if anchor_lines:
        lines.extend([f"- {line}" for line in anchor_lines])

    if evidence_pack and evidence_pack.items:
        ranked = sorted(evidence_pack.items, key=lambda item: (-item.authority_rank, -item.significance))
        for item in ranked[:4]:
            dep_mode = f" [{item.dependency_mode}]" if item.dependency_mode else ""
            lines.append(f"- `{item.path}`{dep_mode}: {item.rationale}")
    else:
        lines.append("- Evidence pack is currently sparse; conclusions are provisional until anchor files are expanded.")

    aux_category = _aux_category(target_path)
    if target_path and "meridian_aux" in target_path and aux_category:
        lines.extend(
            [
                "",
                "### Cross-repo interpretation",
                f"- `{target_path}` is best treated as a **{aux_category}**.",
            ]
        )

    under_tested = False
    if evidence_pack:
        under_tested = evidence_pack.notes and any("under-test" in note.lower() for note in evidence_pack.notes)
        under_tested = bool(under_tested) or any((item.test_coverage_strength or "").lower() in {"weak", "low"} for item in evidence_pack.items)

    if target_path and target_path.endswith("src/meridian_aux/nest/nest.py"):
        under_tested = True

    if under_tested:
        lines.extend(["", "### Uncertainty and risk", "- This area appears under-tested; preserve uncertainty and validate behavior with targeted integration checks."])

    if include_code_tour:
        lines.extend(["", "### Optional code tour", "```python", "# Anchor-first sketch", "for anchor in ['model.py', 'analyzer.py']:", "    print(anchor)", "```"])

    review_flags = ["needs_more_evidence"] if not (evidence_pack and evidence_pack.items) else []
    return DraftOutput(answer_markdown="\n".join(lines), review_flags=review_flags)
