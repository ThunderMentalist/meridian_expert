from __future__ import annotations

import json
from datetime import datetime

from meridian_expert.enums import TaskState
from meridian_expert.investigation.bundle_registry import BundleRegistry
from meridian_expert.investigation.evidence_builder import from_bundle
from meridian_expert.logging_utils import append_jsonl
from meridian_expert.models.artifact import ArtifactRecord
from meridian_expert.orchestration.review_queue import make_item


def run_to_gate(task, store, workspace, brief, require_review: bool = True, lifecycle_stage: str = "mature") -> None:
    tdir = workspace.task_dir(task.task_id)
    cycle = task.current_cycle
    paths = workspace.artifact_paths(task.task_id, cycle, lifecycle_stage=lifecycle_stage)
    store.update_state(task.task_id, TaskState.INVESTIGATING)
    bundles = BundleRegistry().rank_for(task.family.value, brief.package_domain)
    selected = bundles[:2] or BundleRegistry().list()[:1]
    evidence = []
    for b in selected:
        evidence.extend(from_bundle(b))
    ev_path = paths.evidence_bundle()
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    ev_path.write_text("\n".join([f"- {e.path} ({e.bundle})" for e in evidence]), encoding="utf-8")
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="evidence_bundle",
            task_id=task.task_id,
            cycle_id=cycle,
            relative_path=ev_path.relative_to(tdir).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )

    store.update_state(task.task_id, TaskState.DRAFT_READY)
    draft = paths.answer_draft()
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(f"# Draft answer\n\nFamily: {task.family.value}\nGoal: {brief.goal[:200]}\n", encoding="utf-8")
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="answer_draft",
            task_id=task.task_id,
            cycle_id=cycle,
            relative_path=draft.relative_to(tdir).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )
    if require_review:
        store.update_state(task.task_id, TaskState.IN_REVIEW)
        store.create_review_item(make_item(task.task_id, cycle, "draft"))
    append_jsonl(tdir / "logs/events.jsonl", {"ts": datetime.utcnow().isoformat(), "event": "run_to_gate", "state": "IN_REVIEW" if require_review else "DRAFT_READY"})


def deliver(task, store, workspace, prototype: bool = False) -> str:
    tdir = workspace.task_dir(task.task_id)
    cycle = task.current_cycle
    d = "D01"
    lifecycle_stage = "prototype" if prototype else "mature"
    paths = workspace.artifact_paths(task.task_id, cycle, lifecycle_stage=lifecycle_stage, delivery_id=d)
    answer_path = paths.delivery_answer()
    manifest_path = paths.delivery_manifest()
    answer_path.parent.mkdir(parents=True, exist_ok=True)
    answer_path.write_text("# Final answer\nApproved delivery.\n", encoding="utf-8")
    manifest = {
        "task_id": task.task_id,
        "delivery_id": d,
        "lifecycle_stage": lifecycle_stage,
        "reuse_policy": "blocked" if prototype else "allowed",
        "eligible_for_learning": False if prototype else True,
        "eligible_for_golden_promotion": False if prototype else True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="delivery_answer",
            task_id=task.task_id,
            cycle_id=cycle,
            delivery_id=d,
            relative_path=answer_path.relative_to(tdir).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )
    store.insert_artifact(
        ArtifactRecord.for_stage(
            artifact_kind="delivery_manifest",
            task_id=task.task_id,
            cycle_id=cycle,
            delivery_id=d,
            relative_path=manifest_path.relative_to(tdir).as_posix(),
            lifecycle_stage=lifecycle_stage,
        )
    )
    store.update_state(task.task_id, TaskState.DELIVERED)
    return str(answer_path)
