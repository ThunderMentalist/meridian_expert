from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import typer
import yaml
from rich import print

from meridian_expert.enums import TaskState
from meridian_expert.ids import cycle_id, task_id
from meridian_expert.investigation.bundle_registry import BundleRegistry
from meridian_expert.investigation.compatibility_checker import CompatibilityChecker
from meridian_expert.models.task import TaskBrief, TaskRecord
from meridian_expert.orchestration.lifecycle import mode_for
from meridian_expert.orchestration.runner import deliver, run_to_gate
from meridian_expert.orchestration.triage import build_clarification_markdown, triage_from_text
from meridian_expert.settings import resolve_paths
from meridian_expert.storage.repositories import resolve_repositories
from meridian_expert.storage.sqlite_store import SQLiteStore
from meridian_expert.storage.workspace import WorkspaceManager

app = typer.Typer(help="Meridian expert CLI")
task_app = typer.Typer()
review_app = typer.Typer()
compat_app = typer.Typer()
bundle_app = typer.Typer()
learning_app = typer.Typer()
exemplar_app = typer.Typer()
app.add_typer(task_app, name="task")
app.add_typer(review_app, name="review")
app.add_typer(compat_app, name="compat")
app.add_typer(bundle_app, name="bundle")
app.add_typer(learning_app, name="learning")
app.add_typer(exemplar_app, name="exemplar")


REPO_REQUIREMENTS = {
    "meridian": "required_for_real_investigation",
    "meridian_aux": "required_for_real_investigation",
}


def _store_workspace() -> tuple[SQLiteStore, WorkspaceManager]:
    paths = resolve_paths()
    ws = WorkspaceManager(paths.workspace_path)
    ws.ensure()
    store = SQLiteStore(paths.workspace_path / "meridian_expert.db")
    store.init()
    return store, ws


def _load_task_brief(ws: WorkspaceManager, task_id_value: str, cycle_id_value: str) -> TaskBrief | None:
    base = ws.task_dir(task_id_value) / f"cycles/{cycle_id_value}"
    for brief_path in [base / "triage/task_brief.prototype.md", base / "triage/task_brief.md"]:
        if brief_path.exists():
            try:
                return TaskBrief.model_validate_json(brief_path.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def _read_evidence_lines(ws: WorkspaceManager, task_id_value: str, cycle_id_value: str) -> list[str]:
    base = ws.task_dir(task_id_value) / f"cycles/{cycle_id_value}"
    for ev_path in [
        base / "prototype/investigation/evidence_bundle.prototype.md",
        base / "investigation/evidence_bundle.md",
    ]:
        if ev_path.exists():
            return [line.strip().removeprefix("- ") for line in ev_path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("- ")]
    return []


def _review_gate_ready(store: SQLiteStore, task_id_value: str, cycle_id_value: str) -> tuple[bool, str]:
    rows = store.list_review_items_for_task(task_id_value, cycle_id_value)
    if not rows:
        return False, "No review items exist yet for this cycle."
    pending = [r for r in rows if r["status"] == "pending"]
    rejected = [r for r in rows if r["status"] == "rejected"]
    draft_approved = any(r["kind"] == "draft" and r["status"] == "approved" for r in rows)
    if rejected:
        return False, "At least one review item is rejected."
    if pending:
        return False, "Review items are still pending."
    if not draft_approved:
        return False, "Draft review is not approved."
    return True, "All review items approved."


def _ensure_non_prototype_candidate(store: SQLiteStore, task_id_value: str) -> tuple[bool, str]:
    manifest = store.latest_delivery_manifest(task_id_value)
    if manifest is None:
        return False, "Task has no delivery manifest yet."
    if manifest["eligible_for_learning"] == 0:
        return False, "Prototype deliveries are ineligible for learning or exemplar nomination."
    return True, "ok"


def _apply_clarification_update(store: SQLiteStore, ws: WorkspaceManager, rec: TaskRecord, task_id_value: str, heading: str, message: str, event_kind: str) -> None:
    input_path = ws.task_dir(task_id_value) / "input/task.md"
    text = input_path.read_text(encoding="utf-8")
    updated_text = f"{text.rstrip()}\n\n{heading}\n{message.strip()}\n"
    input_path.write_text(updated_text, encoding="utf-8")

    brief = triage_from_text(updated_text)
    lifecycle_stage = mode_for(brief.task_family.value)
    paths = ws.artifact_paths(task_id_value, rec.current_cycle, lifecycle_stage=lifecycle_stage)

    clarifications_path = paths.clarifications()
    clarifications_path.parent.mkdir(parents=True, exist_ok=True)
    clarifications_path.write_text(message.strip() + "\n", encoding="utf-8")

    task_brief_path = paths.task_brief()
    task_brief_path.parent.mkdir(parents=True, exist_ok=True)
    task_brief_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")

    if brief.needs_clarification:
        clarification_request_path = paths.clarification_request()
        clarification_request_path.parent.mkdir(parents=True, exist_ok=True)
        clarification_request_path.write_text(build_clarification_markdown(brief, task_id_value), encoding="utf-8")
        store.update_state(task_id_value, TaskState.NEEDS_CLARIFICATION)
    else:
        store.update_state(task_id_value, TaskState.TRIAGED)

    store.add_event(task_id_value, event_kind, message.strip())


@app.command()
def doctor() -> None:
    paths = resolve_paths()
    repos = resolve_repositories(
        {
            "meridian": paths.meridian_repo_path,
            "meridian_aux": paths.meridian_aux_repo_path,
        }
    )
    repo_checks: dict[str, object] = {}
    missing_required = False
    for repo_name, status in repos.items():
        required_for_real_run = REPO_REQUIREMENTS[repo_name] == "required_for_real_investigation"
        if required_for_real_run and not status.exists:
            missing_required = True
        repo_checks[repo_name] = {
            "configured_path": str(status.configured_path) if status.configured_path else None,
            "exists": status.exists,
            "source_kind": status.source_kind,
            "git_available": status.git_available,
            "root_path": str(status.root_path) if status.root_path else None,
            "required_for_real_investigation": required_for_real_run,
            "notes": status.notes,
        }

    checks = {
        "workspace_exists": paths.workspace_path.exists(),
        "openai_key_present": bool(os.getenv("OPENAI_API_KEY")),
        "repositories": repo_checks,
        "real_investigation_ready": not missing_required,
        "real_investigation_message": (
            "Sibling repositories are configured for local real-repo investigation runs."
            if not missing_required
            else "One or more required sibling repositories are missing; configure local directory paths before running real investigations."
        ),
    }
    for cfg in [
        "config/model_profiles.yaml",
        "config/lifecycle_modes.yaml",
        "config/task_family_policies.yaml",
        "config/bundle_registry.yaml",
        "config/compatibility_manifest.yaml",
    ]:
        try:
            yaml.safe_load(Path(cfg).read_text(encoding="utf-8"))
            checks[f"parse_{cfg}"] = True
        except Exception:
            checks[f"parse_{cfg}"] = False
    print(json.dumps(checks, indent=2))


@task_app.command("create")
def create_task(task_md: Path, attachment: list[Path] = typer.Option(None), related_task_id: str | None = None, parent_task_id: str | None = None) -> None:
    store, ws = _store_workspace()
    existing = store.conn.execute("select count(*) c from tasks where task_id like ?", (f"T-{datetime.utcnow().strftime('%Y%m%d')}-%",)).fetchone()[0]
    tid = task_id(datetime.utcnow(), existing + 1)
    cid = cycle_id(1)
    tdir = ws.create_task_tree(tid, cid)
    shutil.copy(task_md, tdir / "input/task.md")
    attachments = attachment if isinstance(attachment, list) else []
    for a in attachments:
        shutil.copy(a, tdir / "input/attachments" / a.name)
    text = (tdir / "input/task.md").read_text(encoding="utf-8")
    brief = triage_from_text(text)
    lifecycle_stage = mode_for(brief.task_family.value)
    task_brief_path = ws.artifact_paths(tid, cid, lifecycle_stage=lifecycle_stage).task_brief()
    task_brief_path.parent.mkdir(parents=True, exist_ok=True)
    task_brief_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    meta = {"task_id": tid, "current_cycle": cid, "related_task_id": related_task_id, "parent_task_id": parent_task_id}
    (tdir / "meta.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    initial_state = TaskState.NEEDS_CLARIFICATION if brief.needs_clarification else TaskState.TRIAGED
    if brief.needs_clarification:
        clarification_path = ws.artifact_paths(tid, cid, lifecycle_stage=lifecycle_stage).clarification_request()
        clarification_path.parent.mkdir(parents=True, exist_ok=True)
        clarification_path.write_text(build_clarification_markdown(brief, tid), encoding="utf-8")
    store.insert_task(TaskRecord(task_id=tid, state=initial_state, family=brief.task_family, created_at=datetime.utcnow(), current_cycle=cid, parent_task_id=parent_task_id, related_task_id=related_task_id))
    print(tid)


@task_app.command("show")
def show_task(task_id: str, evidence_summary: bool = typer.Option(False, "--evidence-summary")) -> None:
    store, ws = _store_workspace()
    rec = store.get_task(task_id)
    if not rec:
        raise typer.Exit(1)

    payload: dict[str, object] = {
        "task_id": rec.task_id,
        "state": rec.state.value,
        "family": rec.family.value,
        "current_cycle": rec.current_cycle,
        "parent_task_id": rec.parent_task_id,
        "related_task_id": rec.related_task_id,
    }

    brief = _load_task_brief(ws, task_id, rec.current_cycle)
    if brief is not None:
        payload["brief"] = {
            "goal": brief.goal,
            "suggested_bundles": brief.suggested_bundles,
            "candidate_anchor_files": brief.candidate_anchor_files,
            "cross_repo_route": brief.cross_repo_route,
            "hotspot_tier": brief.hotspot_tier,
            "dependency_mode": brief.dependency_mode,
            "is_compatibility_shim": brief.is_compatibility_shim,
            "under_tested_risk": brief.under_tested_risk,
        }

    if evidence_summary:
        selected_bundles = brief.suggested_bundles if brief else []
        selected_tests: list[str] = []
        reg = BundleRegistry()
        for bundle_name in selected_bundles:
            bundle = reg.by_name(bundle_name)
            if bundle:
                selected_tests.extend(bundle.get("supporting_tests", []))
        payload["evidence_summary"] = {
            "selected_anchors": brief.candidate_anchor_files if brief else [],
            "selected_bundles": selected_bundles,
            "selected_tests": list(dict.fromkeys(selected_tests)),
            "cross_repo_route": brief.cross_repo_route if brief else None,
            "hotspot_tier": brief.hotspot_tier if brief else None,
            "dependency_mode": brief.dependency_mode if brief else None,
            "compat_shim_warning": bool(brief and brief.is_compatibility_shim),
            "under_tested_warning": bool(brief and brief.under_tested_risk),
            "evidence_items": _read_evidence_lines(ws, task_id, rec.current_cycle),
        }

    print(json.dumps(payload, indent=2))


@task_app.command("status")
def task_status(task_id: str) -> None:
    store, _ = _store_workspace()
    rec = store.get_task(task_id)
    if not rec:
        raise typer.Exit(1)
    print(json.dumps({"task_id": rec.task_id, "state": rec.state.value, "current_cycle": rec.current_cycle}, indent=2))


@task_app.command("run")
def run_task(task_id: str, to_gate: bool = typer.Option(True, "--to-gate/--through-delivery")) -> None:
    store, ws = _store_workspace()
    rec = store.get_task(task_id)
    if not rec:
        raise typer.Exit(1)
    brief = triage_from_text((ws.task_dir(task_id) / "input/task.md").read_text(encoding="utf-8"))
    lifecycle_stage = mode_for(brief.task_family.value)
    run_to_gate(rec, store, ws, brief, require_review=True, lifecycle_stage=lifecycle_stage)
    if not to_gate:
        ready, msg = _review_gate_ready(store, rec.task_id, rec.current_cycle)
        if not ready:
            raise typer.BadParameter(f"Cannot deliver yet: {msg}")
        out = deliver(rec, store, ws, prototype=lifecycle_stage == "prototype")
        print(out)


@task_app.command("clarify")
def clarify(task_id: str, message: str) -> None:
    store, ws = _store_workspace()
    rec = store.get_task(task_id)
    if not rec:
        raise typer.Exit(1)
    _apply_clarification_update(store, ws, rec, task_id, "## Clarification response", message, "clarification")
    print(f"Clarification recorded for {task_id}: {message}")


@task_app.command("confirm")
def confirm(task_id: str) -> None:
    store, ws = _store_workspace()
    rec = store.get_task(task_id)
    if not rec:
        raise typer.Exit(1)
    message = "Yes, proceed with the current interpretation."
    _apply_clarification_update(
        store,
        ws,
        rec,
        task_id,
        "## Clarification confirmation",
        message,
        "clarification_confirmation",
    )
    print(f"Confirmation recorded for {task_id}: {message}")


@task_app.command("redirect")
def redirect(task_id: str, message: str, new_cycle: bool = False) -> None:
    store, ws = _store_workspace()
    rec = store.get_task(task_id)
    if not rec:
        raise typer.Exit(1)
    if new_cycle:
        n = int(rec.current_cycle[1:]) + 1
        rec.current_cycle = cycle_id(n)
        ws.create_task_tree(task_id, rec.current_cycle)
        store.conn.execute("update tasks set current_cycle=?, state=? where task_id=?", (rec.current_cycle, TaskState.TRIAGED.value, task_id))
        store.conn.execute("insert or ignore into task_cycles values (?,?)", (task_id, rec.current_cycle))
        store.conn.commit()
    store.add_event(task_id, "redirection", json.dumps({"message": message, "new_cycle": new_cycle}))
    print(f"Redirection for {task_id}: {message}")


@task_app.command("follow-on")
def follow_on(source_task_id: str, task_md: Path) -> None:
    store, _ = _store_workspace()
    source = store.get_task(source_task_id)
    if not source:
        raise typer.BadParameter(f"Source task {source_task_id} does not exist")
    if source.state != TaskState.DELIVERED:
        raise typer.BadParameter("Follow-on task creation is only allowed from delivered tasks")
    create_task(task_md, related_task_id=source_task_id, parent_task_id=source_task_id)


@review_app.command("queue")
def review_queue(status: str = typer.Option("pending", "--status"), task_id: str | None = typer.Option(None, "--task-id")) -> None:
    store, _ = _store_workspace()
    rows = store.list_review_items(None if status == "all" else status)
    items = [dict(r) for r in rows]
    if task_id:
        items = [item for item in items if item["task_id"] == task_id]
    print(json.dumps(items, indent=2))


@review_app.command("decide")
def review_decide(review_id: str, decision: str = typer.Argument(..., help="approve or reject")) -> None:
    if decision not in {"approve", "reject"}:
        raise typer.BadParameter("decision must be approve or reject")
    store, _ = _store_workspace()
    row = store.get_review_item(review_id)
    if row is None:
        raise typer.BadParameter(f"Unknown review id {review_id}")

    mapped = "approved" if decision == "approve" else "rejected"
    store.set_review_status(review_id, mapped)
    rec = store.get_task(row["task_id"])
    if rec is not None:
        if mapped == "rejected":
            store.update_state(rec.task_id, TaskState.BLOCKED)
        else:
            ready, _ = _review_gate_ready(store, rec.task_id, rec.current_cycle)
            if ready:
                store.update_state(rec.task_id, TaskState.IN_REVIEW)
    print("ok")


@compat_app.command("check")
def compat_check(changed_file: list[str] = typer.Option(None), markdown_report: bool = False) -> None:
    checker = CompatibilityChecker()
    report = checker.check_changed_paths(changed_file or [])
    if markdown_report:
        print(checker.render_markdown(report))
    else:
        print(report.model_dump_json(indent=2))


@bundle_app.command("list")
def list_bundles() -> None:
    reg = BundleRegistry()
    print(json.dumps([{"name": b["name"], "priority": b.get("priority"), "hotspot_tier": b.get("hotspot_tier")} for b in reg.list()], indent=2))


@bundle_app.command("show")
def show_bundle(name: str) -> None:
    reg = BundleRegistry()
    bundle = reg.by_name(name)
    if bundle is None:
        raise typer.BadParameter(f"Unknown bundle {name}")
    print(json.dumps(bundle, indent=2))


@learning_app.command("nominate")
def learning_nominate(task_id: str) -> None:
    store, _ = _store_workspace()
    ok, msg = _ensure_non_prototype_candidate(store, task_id)
    if not ok:
        raise typer.BadParameter(msg)
    candidate_id = f"LC-{task_id}"
    store.create_learning_candidate(candidate_id, task_id)
    print(candidate_id)


@learning_app.command("list")
def learning_list(status: str = typer.Option("pending", "--status")) -> None:
    store, _ = _store_workspace()
    rows = store.list_learning_candidates(None if status == "all" else status)
    print(json.dumps([dict(r) for r in rows], indent=2))


@learning_app.command("decide")
def learning_decide(candidate_id: str, decision: str = typer.Argument(..., help="approve or reject")) -> None:
    if decision not in {"approve", "reject"}:
        raise typer.BadParameter("decision must be approve or reject")
    store, _ = _store_workspace()
    store.set_learning_candidate_status(candidate_id, "approved" if decision == "approve" else "rejected")
    print("ok")


@exemplar_app.command("nominate")
def exemplar_nominate(task_id: str) -> None:
    store, _ = _store_workspace()
    ok, msg = _ensure_non_prototype_candidate(store, task_id)
    if not ok:
        raise typer.BadParameter(msg)
    candidate_id = f"EC-{task_id}"
    store.create_exemplar_candidate(candidate_id, task_id)
    print(candidate_id)


@exemplar_app.command("list")
def exemplar_list(status: str = typer.Option("pending", "--status")) -> None:
    store, _ = _store_workspace()
    rows = store.list_exemplar_candidates(None if status == "all" else status)
    print(json.dumps([dict(r) for r in rows], indent=2))


@exemplar_app.command("decide")
def exemplar_decide(candidate_id: str, decision: str = typer.Argument(..., help="approve or reject")) -> None:
    if decision not in {"approve", "reject"}:
        raise typer.BadParameter("decision must be approve or reject")
    store, _ = _store_workspace()
    store.set_exemplar_candidate_status(candidate_id, "approved" if decision == "approve" else "rejected")
    print("ok")


if __name__ == "__main__":
    app()
