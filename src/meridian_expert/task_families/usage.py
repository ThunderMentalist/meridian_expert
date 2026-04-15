from __future__ import annotations

import ast
from pathlib import Path

from meridian_expert.models.evidence import EvidencePack


_NAVIGATION_RULES: dict[str, list[str]] = {
    "control_contribution.py": ["meridian/analysis/analyzer.py", "meridian/model/model.py"],
    "predict.py": [
        "meridian/model/model.py",
        "meridian/model/adstock_hill.py",
        "meridian/model/transformers.py",
        "meridian/model/equations.py",
        "meridian/data/input_data.py",
    ],
    "roi.py": ["meridian/analysis/analyzer.py (optimal_freq, summary_metrics)"],
    "residuals.py": ["meridian/analysis/analyzer.py (Analyzer.expected_vs_actual_data)"],
    "actuals_vs_fitted.py": ["meridian/analysis/analyzer.py (Analyzer.expected_vs_actual_data)"],
    "curves.py": ["meridian/analysis/analyzer.py (Analyzer.hill_curves)", "meridian/model/adstock_hill.py"],
    "transformed.py": [
        "meridian/model/model.py",
        "meridian/model/transformers.py",
        "meridian/model/adstock_hill.py",
        "meridian/model/equations.py",
    ],
    "nordic_client.py": ["meridian/analysis/analyzer.py", "src/meridian_aux/contribution/control_contribution.py"],
    "nest.py": ["meridian/analysis/visualizer.py", "meridian/analysis/analyzer.py"],
    "multicollinearity.py": ["meridian/model/model.py", "meridian/model/adstock_hill.py", "meridian/model/transformers.py"],
}


def _guess_target(goal: str, evidence_pack: EvidencePack | None) -> str | None:
    lowered = goal.lower()
    for filename in _NAVIGATION_RULES:
        if filename in lowered:
            return filename

    if evidence_pack:
        for item in evidence_pack.items:
            leaf = item.path.rsplit("/", 1)[-1]
            if leaf in _NAVIGATION_RULES:
                return leaf
    return None


def _grounding_lines(target: str | None, evidence_pack: EvidencePack | None) -> list[str]:
    lines: list[str] = []
    if target and target in _NAVIGATION_RULES:
        lines.append(f"- Start navigation from `{target}` using this route:")
        lines.extend([f"  - `{path}`" for path in _NAVIGATION_RULES[target]])

    if evidence_pack and evidence_pack.items:
        ranked = sorted(evidence_pack.items, key=lambda item: (-item.authority_rank, -item.significance))
        lines.append("- Evidence-backed files in this task:")
        for item in ranked[:4]:
            lines.append(f"  - `{item.path}`: {item.rationale}")

    if not lines:
        lines.append("- Evidence pack is sparse; avoid adding APIs that are not shown in Meridian or meridian_aux surfaces.")
    return lines


def _attachment_snippet_comment(attachment_texts: list[str]) -> str:
    if not attachment_texts:
        return "# Fill in the concrete objects from your repository (e.g., fitted model, analyzer instance)."

    merged = "\n".join(attachment_texts).lower()
    if "analyzer" in merged:
        return "# Adapted for your attachment: reuse your existing Analyzer instance rather than creating a new API."
    if "predict" in merged:
        return "# Adapted for your attachment: keep your existing predict flow and only swap verified Meridian surfaces."
    return "# Adapted for your attachment: align variable names with your local code snippet."


def _make_snippet(target: str | None, attachment_texts: list[str]) -> str | None:
    comment = _attachment_snippet_comment(attachment_texts)

    if target == "predict.py":
        code = "\n".join(
            [
                "from meridian.model.model import Meridian",
                "from meridian.data.input_data import InputData",
                "",
                "# Existing Meridian flow: fitted model object + validated input coordinates.",
                comment,
                "model: Meridian = fitted_model  # provided by your pipeline",
                "future_inputs: InputData = prepared_future_inputs  # provided by your pipeline",
                "forecast = model.fit(future_inputs)",
                "print(forecast)",
            ]
        )
    elif target:
        code = "\n".join(
            [
                "# Usage template grounded in known surfaces.",
                comment,
                "# Replace placeholders with real objects from your project.",
                "result = existing_object  # noqa: F821",
                "print(result)",
            ]
        )
    else:
        return None

    ast.parse(code)
    return code


def generate_answer(
    goal: str,
    evidence_pack: EvidencePack | None = None,
    *,
    attachment_texts: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Generate practical usage guidance grounded in known Meridian/aux surfaces."""

    attachment_texts = attachment_texts or []
    target = _guess_target(goal, evidence_pack)

    lines: list[str] = [
        "## Usage guidance",
        "",
        "### Recommended approach",
        "Use existing Meridian or meridian_aux surfaces that are visible in evidence; do not invent new helper APIs.",
        "",
        "### Grounding and navigation",
        *(_grounding_lines(target, evidence_pack)),
    ]

    if attachment_texts:
        lines.extend(
            [
                "",
                "### Attachment-aware adaptation",
                f"- Tailored this guidance to {len(attachment_texts)} attachment(s) without mutating those files.",
                "- Keep your current object lifecycle and replace only the specific surfaces listed above.",
            ]
        )

    lines.extend(
        [
            "",
            "### Guardrails",
            "- If a method/class is not present in evidence or known navigation routes, mark it as unverified instead of fabricating it.",
            "- Prefer analyzer/model/input-data paths listed above for compatibility-sensitive integrations.",
        ]
    )

    snippets: list[str] = []
    snippet = _make_snippet(target, attachment_texts)
    if snippet:
        snippets.append(snippet)

    return "\n".join(lines), snippets


def load_attachment_texts(attachments_dir: Path) -> list[str]:
    if not attachments_dir.exists():
        return []
    texts: list[str] = []
    for path in sorted(attachments_dir.glob("*")):
        if path.is_file() and path.suffix in {".py", ".txt", ".md", ".json", ".yaml", ".yml"}:
            texts.append(path.read_text(encoding="utf-8"))
    return texts
