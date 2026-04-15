from meridian_expert.models.evidence import EvidenceItem, EvidencePack
from meridian_expert.task_families.formatter import format_output
from meridian_expert.task_families.reviewer import review_draft
from meridian_expert.task_families.theory import generate_answer


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        anchor_files=["meridian/model/model.py", "meridian/analysis/analyzer.py"],
        items=[
            EvidenceItem(
                repo_name="meridian",
                path="meridian/model/model.py",
                rationale="Facade orchestration over transforms and equations.",
                authority_rank=10,
                significance=0.9,
                direct=True,
                dependency_mode="semi_internal",
            ),
            EvidenceItem(
                repo_name="meridian",
                path="meridian/analysis/analyzer.py",
                rationale="Consumes fitted model internals.",
                authority_rank=9,
                significance=0.8,
                direct=True,
                dependency_mode="publicish_output",
            ),
        ],
    )


def test_theory_model_py_reflects_cross_file_reasoning() -> None:
    draft = generate_answer(
        "Explain Meridian model behavior",
        _evidence_pack(),
        target_path="meridian/model/model.py",
    )

    lowered = draft.answer_markdown.lower()
    assert "orchestration façade" in lowered or "orchestration facade" in lowered
    assert "analyzer" in lowered


def test_theory_analyzer_reflects_model_dependencies() -> None:
    draft = generate_answer(
        "Explain analyzer behavior",
        _evidence_pack(),
        target_path="meridian/analysis/analyzer.py",
    )

    lowered = draft.answer_markdown.lower()
    assert "downstream consumer" in lowered
    assert "model" in lowered


def test_theory_control_contribution_categorized_as_compat_shim() -> None:
    draft = generate_answer(
        "Explain control contribution behavior",
        _evidence_pack(),
        target_path="src/meridian_aux/contribution/control_contribution.py",
    )

    assert "compatibility shim" in draft.answer_markdown.lower()


def test_reviewer_rejects_model_py_self_sufficient_claim() -> None:
    bad_draft = generate_answer(
        "Explain model",
        _evidence_pack(),
        target_path="meridian/model/model.py",
    )
    bad_draft.answer_markdown = "model.py fully proves behavior and is self-contained."

    decision = review_draft(
        bad_draft,
        goal="Explain model",
        evidence_pack=_evidence_pack(),
        target_path="meridian/model/model.py",
    )

    assert decision.status == "reject"
    assert any("self-sufficient" in issue for issue in decision.issues)


def test_reviewer_flags_missing_under_tested_note_for_nest() -> None:
    draft = generate_answer(
        "Explain nest bridge",
        _evidence_pack(),
        target_path="src/meridian_aux/nest/nest.py",
    )
    draft.answer_markdown = "## Conceptual explanation\n\nBridge behavior summary with evidence anchors."

    decision = review_draft(
        draft,
        goal="Explain nest bridge",
        evidence_pack=_evidence_pack(),
        target_path="src/meridian_aux/nest/nest.py",
    )

    assert decision.status == "revise"
    assert any("under-tested" in issue for issue in decision.issues)


def test_formatter_shapes_prose_bullets_and_mixed() -> None:
    draft = generate_answer("Explain adstock", _evidence_pack(), target_path="meridian/model/model.py")
    draft.snippets = ["print('demo')"]

    prose = format_output(draft, style="prose_markdown")
    bullets = format_output(draft, style="bullet_markdown")
    mixed = format_output(draft, style="mixed_markdown")

    assert prose.startswith("## Theory answer")
    assert bullets.startswith("- ")
    assert "## Snippet" in mixed
    assert "```python" in mixed
