from __future__ import annotations

from meridian_expert.models.evidence import EvidencePack
from meridian_expert.orchestration.runner import DraftOutput, ReviewDecision
from meridian_expert.task_families.theory import _aux_category


_OVERCLAIM_MARKERS = ("always", "definitive", "proves", "guaranteed")


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def review_draft(
    draft: DraftOutput,
    *,
    goal: str,
    evidence_pack: EvidencePack | None = None,
    target_path: str | None = None,
    family: str = "theory",
) -> ReviewDecision:
    issues: list[str] = []
    suggested_edits: list[str] = []
    text = draft.answer_markdown
    lowered = text.lower()

    if family != "theory":
        issues.append("Wrong-family behavior: reviewer expected a theory-family draft.")
        suggested_edits.append("Re-run the correct family or restate answer in conceptual theory format.")

    if not _has_any(lowered, ("conceptual", "explanation")):
        issues.append("Audience fit: draft should lead with a conceptual explanation section.")
        suggested_edits.append("Add a concise conceptual-first section before implementation details.")

    if _has_any(lowered, _OVERCLAIM_MARKERS) and "uncert" not in lowered:
        issues.append("Overclaiming beyond evidence: certainty language appears without uncertainty framing.")
        suggested_edits.append("Replace absolute wording with evidence-bounded language.")

    if target_path and target_path.endswith("meridian/model/model.py"):
        if "façade" not in lowered and "facade" not in lowered:
            issues.append("`model.py` treated as self-sufficient; missing façade/orchestrator framing.")
            suggested_edits.append("State explicitly that model.py orchestrates behavior across multiple model files.")
        if "analyzer" not in lowered:
            issues.append("Cross-file reasoning gap: analyzer dependency not mentioned for model.py theory explanation.")
            suggested_edits.append("Mention analyzer as a downstream consumer of model internals.")

    if target_path and target_path.endswith("meridian/analysis/analyzer.py") and "model" not in lowered:
        issues.append("Analyzer explanation is isolated from model-side dependencies.")
        suggested_edits.append("Explain analyzer behavior as downstream of fitted model internals.")

    if target_path and "meridian_aux" in target_path:
        aux_category = _aux_category(target_path)
        if aux_category and aux_category.split(" ")[0] not in lowered:
            issues.append("Aux categorization missing or incorrect for cross-repo explanation.")
            suggested_edits.append(f"Identify `{target_path}` as `{aux_category}`.")

    if target_path and target_path.endswith("src/meridian_aux/nest/nest.py"):
        if "under-test" not in lowered and "coverage" not in lowered and "weak" not in lowered:
            issues.append("Missing under-tested risk note for nest bridge behavior.")
            suggested_edits.append("Add an explicit note that nest.py is meaningfully coupled and weakly covered.")

    if evidence_pack and evidence_pack.items and "evidence" not in lowered and "anchor" not in lowered:
        issues.append("Conceptual correctness gate: evidence pack exists but answer does not cite grounding.")
        suggested_edits.append("Add an evidence-grounding section referencing anchor files.")

    if any("self-sufficient" in issue for issue in issues):
        return ReviewDecision(status="reject", issues=issues, suggested_edits=suggested_edits)
    if issues:
        return ReviewDecision(status="revise", issues=issues, suggested_edits=suggested_edits)
    return ReviewDecision(status="approve", issues=[], suggested_edits=[])


def review_passes(draft: str) -> bool:
    decision = review_draft(DraftOutput(answer_markdown=draft), goal="unspecified")
    return decision.status == "approve"
