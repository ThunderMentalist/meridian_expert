from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from meridian_expert.enums import TaskFamily, TaskState
from meridian_expert.investigation.bundle_registry import BundleRegistry
from meridian_expert.investigation.evidence_builder import from_bundle
from meridian_expert.llm.client import LLMClient
from meridian_expert.llm.prompt_loader import load_prompt
from meridian_expert.logging_utils import append_jsonl
from meridian_expert.models.artifact import ArtifactRecord
from meridian_expert.orchestration.review_queue import make_item
from meridian_expert.orchestration.router import route_family
from meridian_expert.task_families.usage import generate_answer as generate_usage_answer, load_attachment_texts
from meridian_expert.settings import resolve_paths
from meridian_expert.storage.repositories import resolve_repositories


class RunOptions(BaseModel):
    through_delivery: bool = False
    to_gate: bool = False
    stream: bool = False
    bypass_review_for_tests: bool = False


class DraftOutput(BaseModel):
    answer_markdown: str
    appendix_markdown: str | None = None
    snippets: list[str] = Field(default_factory=list)
    review_flags: list[str] = Field(default_factory=list)
    clarification_needed: bool = False
    clarification_questions: list[str] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    status: Literal["approve", "reject", "revise"]
    issues: list[str] = Field(default_factory=list)
    suggested_edits: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    decision: ReviewDecision
    blocked_for_manual_review: bool = False


def _artifact_stage(prototype: bool) -> str:
    return "prototype" if prototype else "mature"


def _requires_real_investigation(brief) -> bool:
    return not brief.needs_clarification


def _parse_evidence_markdown(evidence_markdown: str):
    from meridian_expert.models.evidence import EvidenceItem, EvidencePack

    items: list[EvidenceItem] = []
    for line in evidence_markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        payload = stripped.removeprefix("- ")
        path = payload.split(" (", 1)[0].strip()
        rationale = payload.split("(", 1)[1].rstrip(")") if "(" in payload and payload.endswith(")") else "Evidence from investigation bundle."
        if not path:
            continue
        items.append(
            EvidenceItem(
                repo_name="meridian_aux" if path.startswith("src/meridian_aux/") else "meridian",
                path=path,
                rationale=rationale,
                authority_rank=5,
                significance=0.5,
                direct=True,
            )
        )
    anchors = [item.path for item in items[:2]]
    return EvidencePack(anchor_files=anchors, items=items)


def _validated_python_snippets(snippets: list[str]) -> list[str]:
    validated: list[str] = []
    for snippet in snippets:
        ast.parse(snippet)
        validated.append(snippet)
    return validated


def run_triage_stage(task, store, workspace, brief, *, lifecycle_stage: str, require_review: bool) -> bool:
    if brief.needs_clarification:
        paths = workspace.artifact_paths(task.task_id, task.current_cycle, lifecycle_stage=lifecycle_stage)
        clarification = paths.clarification_request()
        clarification.parent.mkdir(parents=True, exist_ok=True)
        body = "# Clarification required\n\n" + "\n".join(f"- {q}" for q in brief.clarification_questions)
        clarification.write_text(body + "\n", encoding="utf-8")
        store.insert_artifact(
            ArtifactRecord.for_stage(
                artifact_kind="clarification_request",
                task_id=task.task_id,
                cycle_id=task.current_cycle,
                relative_path=clarification.relative_to(workspace.task_dir(task.task_id)).as_posix(),
                lifecycle_stage=lifecycle_stage,
            )
        )
        store.update_state(task.task_id, TaskState.NEEDS_CLARIFICATION)
        if require_review:
            store.create_review_item(make_item(task.task_id, task.current_cycle, "task_brief"))
        return False

    store.update_state(task.task_id, TaskState.TRIAGED)
    if require_review and lifecycle_stage == "prototype":
        store.create_review_item(make_item(task.task_id, task.current_cycle, "task_brief"))
    return True


def run_investigation_stage(task, store, workspace, brief, *, lifecycle_stage: str) -> tuple[bool, str]:
    store.update_state(task.task_id, TaskState.INVESTIGATING)
    paths = resolve_paths()
    repo_status = resolve_repositories(
        {
            "meridian": paths.meridian_repo_path,
            "meridian_aux": paths.meridian_aux_repo_path,
        }
    )

    if _requires_real_investigation(brief):
        missing = [name for name, status in repo_status.items() if not status.exists]
        if missing:
            art = workspace.artifact_paths(task.task_id, task.current_cycle, lifecycle_stage=lifecycle_stage)
            blocker = art.evidence_bundle()
            blocker.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                "# Investigation blocked",
                "",
                "Real local sibling repositories are required for investigation runs.",
                "Configure MERIDIAN_REPO_PATH and MERIDIAN_AUX_REPO_PATH to valid directories.",
                "",
                "Missing repositories:",
                *[f"- {name}" for name in missing],
            ]
            blocker.write_text("\n".join(lines) + "\n", encoding="utf-8")
            store.insert_artifact(
                ArtifactRecord.for_stage(
                    artifact_kind="investigation_blocker",
                    task_id=task.task_id,
                    cycle_id=task.current_cycle,
                    relative_path=blocker.relative_to(workspace.task_dir(task.task_id)).as_posix(),
                    lifecycle_stage=lifecycle_stage,
                )
            )
            store.update_state(task.task_id, TaskState.BLOCKED)
            return False, blocker.read_text(encoding="utf-8")

    bundles = BundleRegistry().rank_for(task.family.value, brief.package_domain)
    selected = bundles[:2] or BundleRegistry().list()[:1]
    evidence = []
    for bundle in selected:
        evidence.extend(from_bundle(bundle))
    evidence_md = "\n".join(f"- {e.path} ({e.rationale})" for e in evidence)

    art = workspace.artifact_paths(task.task_id, task.current_cycle, lifecycle_stage=lifecycle_stage)
    ev_path = art.evidence_bundle()
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.write_text(evidence_md + "\n", encoding="utf-8")
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="evidence_bundle",
            task_id=task.task_id,
            cycle_id=task.current_cycle,
            relative_path=ev_path.relative_to(workspace.task_dir(task.task_id)).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )
    return True, evidence_md


def run_family_stage(task, brief, evidence_markdown: str, workspace, *, llm_client: LLMClient, stream: bool) -> DraftOutput:
    family = route_family(explicit=None, triaged=TaskFamily(task.family), builder_enabled=False)

    if family == TaskFamily.USAGE:
        evidence_pack = _parse_evidence_markdown(evidence_markdown)
        attachments = load_attachment_texts(workspace.task_dir(task.task_id) / "input" / "attachments")
        answer, snippets = generate_usage_answer(brief.goal, evidence_pack, attachment_texts=attachments)
        appendix = "## Appendix\n\n- Deterministic prototype appendix." if brief.appendix_requested else None
        return DraftOutput(answer_markdown=answer, appendix_markdown=appendix, snippets=snippets)

    prompt = load_prompt(family.value)
    input_text = f"Goal:\n{brief.goal}\n\nEvidence:\n{evidence_markdown}\n"
    answer = llm_client.generate_text(
        family.value,
        instructions=prompt,
        input_text=input_text,
        stream=stream,
        metadata={"task_id": task.task_id, "cycle_id": task.current_cycle, "stage": "family", "prompt_spec_name": family.value},
    )
    snippets: list[str] = []
    if brief.snippets_allowed:
        snippets.append("# snippet\nprint('prototype snippet')")
    appendix = "## Appendix\n\n- Deterministic prototype appendix." if brief.appendix_requested else None
    return DraftOutput(answer_markdown=answer, appendix_markdown=appendix, snippets=snippets)


def run_review_stage(task, store, workspace, draft: DraftOutput, *, llm_client: LLMClient, lifecycle_stage: str, require_review: bool, bypass_review_for_tests: bool) -> ReviewResult:
    if require_review:
        store.create_review_item(make_item(task.task_id, task.current_cycle, "draft"))

    prompt = load_prompt("reviewer")
    reviewer_output = llm_client.generate_structured(
        "reviewer",
        instructions=prompt,
        input_text=draft.answer_markdown,
        schema_model=ReviewDecision,
        metadata={"task_id": task.task_id, "cycle_id": task.current_cycle, "stage": "review", "prompt_spec_name": "reviewer"},
    )
    decision = ReviewDecision.model_validate(reviewer_output)

    art = workspace.artifact_paths(task.task_id, task.current_cycle, lifecycle_stage=lifecycle_stage)
    notes = art.review_notes()
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("\n".join([f"# Review: {decision.status}", *[f"- {i}" for i in decision.issues]]) + "\n", encoding="utf-8")
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="review_notes",
            task_id=task.task_id,
            cycle_id=task.current_cycle,
            relative_path=notes.relative_to(workspace.task_dir(task.task_id)).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )
    art.decision_json().write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    if require_review and lifecycle_stage == "prototype" and not bypass_review_for_tests:
        store.update_state(task.task_id, TaskState.IN_REVIEW)
        return ReviewResult(decision=decision, blocked_for_manual_review=True)

    if decision.status == "reject":
        store.update_state(task.task_id, TaskState.BLOCKED)
    else:
        store.update_state(task.task_id, TaskState.IN_REVIEW)
    return ReviewResult(decision=decision, blocked_for_manual_review=False)


def persist_draft_stage(task, store, workspace, draft: DraftOutput, *, lifecycle_stage: str) -> None:
    art = workspace.artifact_paths(task.task_id, task.current_cycle, lifecycle_stage=lifecycle_stage)
    task_dir = workspace.task_dir(task.task_id)

    answer = art.answer_draft()
    answer.parent.mkdir(parents=True, exist_ok=True)
    answer.write_text(draft.answer_markdown + "\n", encoding="utf-8")
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="answer_draft",
            task_id=task.task_id,
            cycle_id=task.current_cycle,
            relative_path=answer.relative_to(task_dir).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )

    if draft.appendix_markdown:
        appendix = art.appendix_draft()
        appendix.write_text(draft.appendix_markdown + "\n", encoding="utf-8")
        store.insert_artifact(
            ArtifactRecord.for_stage(
                artifact_kind="appendix_draft",
                task_id=task.task_id,
                cycle_id=task.current_cycle,
                relative_path=appendix.relative_to(task_dir).as_posix(),
                lifecycle_stage=lifecycle_stage,
            )
        )

    for idx, snippet in enumerate(_validated_python_snippets(draft.snippets), start=1):
        snippet_path = answer.parent / "snippets" / f"example_{idx:02d}.py"
        snippet_path.parent.mkdir(parents=True, exist_ok=True)
        snippet_path.write_text(snippet + "\n", encoding="utf-8")
        store.insert_artifact(
            ArtifactRecord.for_stage(
                artifact_kind="snippet_draft",
                task_id=task.task_id,
                cycle_id=task.current_cycle,
                relative_path=snippet_path.relative_to(task_dir).as_posix(),
                lifecycle_stage=lifecycle_stage,
            )
        )

    store.update_state(task.task_id, TaskState.DRAFT_READY)


def deliver_stage(task, store, workspace, draft: DraftOutput, *, lifecycle_stage: str, delivery_id: str = "D01") -> str:
    task_dir = workspace.task_dir(task.task_id)
    paths = workspace.artifact_paths(task.task_id, task.current_cycle, lifecycle_stage=lifecycle_stage, delivery_id=delivery_id)
    answer_path = paths.delivery_answer()
    answer_path.parent.mkdir(parents=True, exist_ok=True)
    answer_path.write_text(draft.answer_markdown + "\n", encoding="utf-8")

    if draft.appendix_markdown:
        appendix_path = paths.delivery_appendix()
        appendix_path.write_text(draft.appendix_markdown + "\n", encoding="utf-8")
        store.insert_artifact(
            ArtifactRecord.for_stage(
                artifact_kind="delivery_appendix",
                task_id=task.task_id,
                cycle_id=task.current_cycle,
                delivery_id=delivery_id,
                relative_path=appendix_path.relative_to(task_dir).as_posix(),
                lifecycle_stage=lifecycle_stage,
            )
        )

    snippet_files: list[str] = []
    for idx, snippet in enumerate(_validated_python_snippets(draft.snippets), start=1):
        snippet_path = answer_path.parent / (f"example_{idx:02d}.prototype.py" if lifecycle_stage == "prototype" else f"example_{idx:02d}.py")
        snippet_path.write_text(snippet + "\n", encoding="utf-8")
        snippet_files.append(snippet_path.name)
        store.insert_artifact(
            ArtifactRecord.for_stage(
                artifact_kind="delivery_snippet",
                task_id=task.task_id,
                cycle_id=task.current_cycle,
                delivery_id=delivery_id,
                relative_path=snippet_path.relative_to(task_dir).as_posix(),
                lifecycle_stage=lifecycle_stage,
            )
        )

    manifest_path = paths.delivery_manifest()
    manifest = {
        "task_id": task.task_id,
        "cycle_id": task.current_cycle,
        "delivery_id": delivery_id,
        "lifecycle_stage": lifecycle_stage,
        "created_at": datetime.now(UTC).isoformat(),
        "prototype": lifecycle_stage == "prototype",
        "reuse_policy": "blocked" if lifecycle_stage == "prototype" else "allowed",
        "eligible_for_learning": lifecycle_stage != "prototype",
        "eligible_for_golden_promotion": lifecycle_stage != "prototype",
        "snippet_files": snippet_files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="delivery_answer",
            task_id=task.task_id,
            cycle_id=task.current_cycle,
            delivery_id=delivery_id,
            relative_path=answer_path.relative_to(task_dir).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="delivery_manifest",
            task_id=task.task_id,
            cycle_id=task.current_cycle,
            delivery_id=delivery_id,
            relative_path=manifest_path.relative_to(task_dir).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )
    store.update_state(task.task_id, TaskState.DELIVERED)
    return str(answer_path)


def run_task(task, store, workspace, brief, *, llm_client: LLMClient | None = None, options: RunOptions | None = None, lifecycle_stage: str = "mature", require_review: bool = True) -> str | None:
    llm_client = llm_client or LLMClient()
    options = options or RunOptions(to_gate=True)

    ready = run_triage_stage(task, store, workspace, brief, lifecycle_stage=lifecycle_stage, require_review=require_review)
    if not ready:
        return None

    can_investigate, evidence = run_investigation_stage(task, store, workspace, brief, lifecycle_stage=lifecycle_stage)
    if not can_investigate:
        return None

    draft = run_family_stage(task, brief, evidence, workspace, llm_client=llm_client, stream=options.stream)
    persist_draft_stage(task, store, workspace, draft, lifecycle_stage=lifecycle_stage)

    review_result = run_review_stage(
        task,
        store,
        workspace,
        draft,
        llm_client=llm_client,
        lifecycle_stage=lifecycle_stage,
        require_review=require_review,
        bypass_review_for_tests=options.bypass_review_for_tests,
    )
    if review_result.blocked_for_manual_review:
        append_jsonl(
            workspace.task_dir(task.task_id) / "logs/events.jsonl",
            {"ts": datetime.now(UTC).isoformat(), "event": "awaiting_review", "task_id": task.task_id, "cycle_id": task.current_cycle},
        )
        return None

    if options.to_gate and not options.through_delivery:
        return None
    return deliver_stage(task, store, workspace, draft, lifecycle_stage=lifecycle_stage)


def run_to_gate(task, store, workspace, brief, require_review: bool = True, lifecycle_stage: str = "mature") -> None:
    run_task(
        task,
        store,
        workspace,
        brief,
        options=RunOptions(to_gate=True, through_delivery=False),
        lifecycle_stage=lifecycle_stage,
        require_review=require_review,
    )


def deliver(task, store, workspace, prototype: bool = False) -> str:
    lifecycle_stage = _artifact_stage(prototype)
    art = workspace.artifact_paths(task.task_id, task.current_cycle, lifecycle_stage=lifecycle_stage)
    answer = art.answer_draft()
    appendix = art.appendix_draft()
    snippets_dir = answer.parent / "snippets"

    draft = DraftOutput(answer_markdown=answer.read_text(encoding="utf-8") if answer.exists() else "# Final answer\n")
    if appendix.exists():
        draft.appendix_markdown = appendix.read_text(encoding="utf-8")
    if snippets_dir.exists():
        for snippet_file in sorted(snippets_dir.glob("*.py")):
            draft.snippets.append(snippet_file.read_text(encoding="utf-8"))

    return deliver_stage(task, store, workspace, draft, lifecycle_stage=lifecycle_stage)
