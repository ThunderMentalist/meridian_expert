from __future__ import annotations

import json
from datetime import datetime

from meridian_expert.enums import TaskState
from meridian_expert.investigation.bundle_registry import BundleRegistry
from meridian_expert.investigation.evidence_builder import from_bundle
from meridian_expert.logging_utils import append_jsonl
from meridian_expert.orchestration.review_queue import make_item


def run_to_gate(task, store, workspace, brief, require_review: bool = True) -> None:
    tdir = workspace.task_dir(task.task_id)
    cycle = task.current_cycle
    store.update_state(task.task_id, TaskState.INVESTIGATING)
    bundles = BundleRegistry().rank_for(task.family.value, brief.package_domain)
    selected = bundles[:2] or BundleRegistry().list()[:1]
    evidence = []
    for b in selected:
        evidence.extend(from_bundle(b))
    ev_path = tdir / f"cycles/{cycle}/investigation/evidence_bundle.md"
    ev_path.write_text("\n".join([f"- {e.path} ({e.bundle})" for e in evidence]), encoding="utf-8")
    store.update_state(task.task_id, TaskState.DRAFT_READY)
    draft = tdir / f"cycles/{cycle}/draft/answer_draft.md"
    draft.write_text(f"# Draft answer\n\nFamily: {task.family.value}\nGoal: {brief.goal[:200]}\n", encoding="utf-8")
    if require_review:
        store.update_state(task.task_id, TaskState.IN_REVIEW)
        store.create_review_item(make_item(task.task_id, cycle, "draft"))
    append_jsonl(tdir / "logs/events.jsonl", {"ts": datetime.utcnow().isoformat(), "event": "run_to_gate", "state": "IN_REVIEW" if require_review else "DRAFT_READY"})


def deliver(task, store, workspace, prototype: bool = False) -> str:
    tdir = workspace.task_dir(task.task_id)
    cycle = task.current_cycle
    d = "D01"
    base = tdir / (f"deliveries/prototype/{d}" if prototype else f"deliveries/{d}")
    base.mkdir(parents=True, exist_ok=True)
    ans_name = "answer.prototype.md" if prototype else "answer.md"
    manifest_name = "manifest.prototype.json" if prototype else "manifest.json"
    (base / ans_name).write_text("# Final answer\nApproved delivery.\n", encoding="utf-8")
    manifest = {"task_id": task.task_id, "delivery_id": d, "lifecycle_stage": "prototype" if prototype else "mature", "reuse_policy": "blocked" if prototype else "allowed", "eligible_for_learning": False if prototype else True, "eligible_for_golden_promotion": False if prototype else True}
    (base / manifest_name).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    store.update_state(task.task_id, TaskState.DELIVERED)
    return str(base / ans_name)
