from __future__ import annotations

from meridian_expert.orchestration.runner import DraftOutput


def _normalize_draft(draft: DraftOutput | str) -> DraftOutput:
    if isinstance(draft, DraftOutput):
        return draft
    return DraftOutput(answer_markdown=draft)


def format_output(draft: DraftOutput | str, style: str = "prose_markdown") -> str:
    payload = _normalize_draft(draft)
    answer = payload.answer_markdown.strip()
    snippets = payload.snippets

    if style in {"markdown", "prose_markdown", "prose"}:
        return answer

    if style in {"bullet_markdown", "bullets"}:
        sentences = [segment.strip() for segment in answer.replace("\n", " ").split(".") if segment.strip()]
        bullets = [f"- {segment}." for segment in sentences]
        return "\n".join(bullets)

    if style in {"mixed_markdown", "mixed", "explanation_snippet"}:
        lines = ["## Explanation", "", answer]
        if snippets:
            lines.extend(["", "## Snippet", "", "```python", snippets[0].strip(), "```"])
        return "\n".join(lines)

    if style in {"faq_markdown", "faq"}:
        lines = ["## FAQ", "", "### What is the main point?", answer]
        if payload.review_flags:
            lines.extend(["", "### What should be validated next?", "; ".join(payload.review_flags)])
        return "\n\n".join(lines)

    return answer
