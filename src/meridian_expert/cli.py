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
from meridian_expert.models.task import TaskRecord
from meridian_expert.orchestration.lifecycle import mode_for
from meridian_expert.orchestration.runner import deliver, run_to_gate
from meridian_expert.orchestration.triage import triage_from_text
from meridian_expert.settings import resolve_paths
from meridian_expert.storage.repositories import resolve_repositories
from meridian_expert.storage.sqlite_store import SQLiteStore
from meridian_expert.storage.workspace import WorkspaceManager

app = typer.Typer(help="Meridian expert CLI")
task_app = typer.Typer()
review_app = typer.Typer()
compat_app = typer.Typer()
bundle_app = typer.Typer()
app.add_typer(task_app, name="task")
app.add_typer(review_app, name="review")
app.add_typer(compat_app, name="compat")
app.add_typer(bundle_app, name="bundle")


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
    for a in attachment or []:
        shutil.copy(a, tdir / "input/attachments" / a.name)
    text = (tdir / "input/task.md").read_text(encoding="utf-8")
    brief = triage_from_text(text)
    lifecycle_stage = mode_for(brief.task_family.value)
    task_brief_path = ws.artifact_paths(tid, cid, lifecycle_stage=lifecycle_stage).task_brief()
    task_brief_path.parent.mkdir(parents=True, exist_ok=True)
    task_brief_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    meta = {"task_id": tid, "current_cycle": cid, "related_task_id": related_task_id, "parent_task_id": parent_task_id}
    (tdir / "meta.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    store.insert_task(TaskRecord(task_id=tid, state=TaskState.TRIAGED, family=brief.task_family, created_at=datetime.utcnow(), current_cycle=cid, parent_task_id=parent_task_id, related_task_id=related_task_id))
    print(tid)


@task_app.command("show")
def show_task(task_id: str) -> None:
    store, ws = _store_workspace()
    rec = store.get_task(task_id)
    if not rec:
        raise typer.Exit(1)
    print(rec.model_dump_json(indent=2))
    base = ws.task_dir(task_id) / f"cycles/{rec.current_cycle}"
    for brief in [base / "triage/task_brief.md", base / "prototype/triage/task_brief.prototype.md"]:
        if brief.exists():
            print(brief.read_text(encoding="utf-8"))
            break


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
        out = deliver(rec, store, ws, prototype=lifecycle_stage == "prototype")
        print(out)


@task_app.command("clarify")
def clarify(task_id: str, message: str) -> None:
    _store_workspace()
    print(f"Clarification recorded for {task_id}: {message}")


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
        store.conn.execute("update tasks set current_cycle=? where task_id=?", (rec.current_cycle, task_id))
        store.conn.execute("insert or ignore into task_cycles values (?,?)", (task_id, rec.current_cycle))
        store.conn.commit()
    print(f"Redirection for {task_id}: {message}")


@task_app.command("follow-on")
def follow_on(source_task_id: str, task_md: Path) -> None:
    create_task(task_md, related_task_id=source_task_id, parent_task_id=source_task_id)


@review_app.command("queue")
def review_queue() -> None:
    store, _ = _store_workspace()
    rows = store.list_review_items()
    print(json.dumps([dict(r) for r in rows], indent=2))


@review_app.command("decide")
def review_decide(review_id: str, decision: str = typer.Argument(..., help="approve or reject")) -> None:
    store, _ = _store_workspace()
    store.set_review_status(review_id, "approved" if decision == "approve" else "rejected")
    print("ok")


@compat_app.command("check")
def compat_check(changed_file: list[str] = typer.Option(None), markdown_report: bool = False) -> None:
    checker = CompatibilityChecker()
    findings = checker.run(changed_file or [])
    if markdown_report:
        lines = ["# Compatibility risk report", ""]
        for f in findings:
            lines.append(f"- {f.upstream}: changed={f.changed}, risk={f.risk_level}")
        print("\n".join(lines))
    else:
        print(json.dumps([f.model_dump() for f in findings], indent=2))


@bundle_app.command("list")
def list_bundles() -> None:
    reg = BundleRegistry()
    print(json.dumps([{"name": b["name"], "priority": b.get("priority")} for b in reg.list()], indent=2))


if __name__ == "__main__":
    app()
