from __future__ import annotations

from datetime import datetime
from pathlib import Path

from meridian_expert.enums import TaskFamily, TaskState
from meridian_expert.llm.client import DeterministicFakeBackend, LLMClient
from meridian_expert.llm.profiles import ModelProfile
from meridian_expert.models.task import TaskRecord
from meridian_expert.orchestration.runner import RunOptions, run_task
from meridian_expert.orchestration.triage import deterministic_triage_from_text
from meridian_expert.storage.sqlite_store import SQLiteStore
from meridian_expert.storage.workspace import WorkspaceManager
from meridian_expert.testing_support.repo_fixtures import build_fixture_workspace


def _llm_client() -> LLMClient:
    profiles = {
        "theory": ModelProfile(alias="theory", model="gpt-test", reasoning_effort="medium"),
        "usage": ModelProfile(alias="usage", model="gpt-test", reasoning_effort="medium"),
        "updates": ModelProfile(alias="updates", model="gpt-test", reasoning_effort="medium"),
        "reviewer": ModelProfile(alias="reviewer", model="gpt-test", reasoning_effort="low"),
    }
    return LLMClient(backend=DeterministicFakeBackend(), profiles=profiles)


def _setup_task(tmp_path: Path) -> tuple[SQLiteStore, WorkspaceManager, TaskRecord]:
    ws = WorkspaceManager(tmp_path / "runtime")
    ws.ensure()
    task_id = "T-20260415-0001"
    cycle_id = "C01"
    ws.create_task_tree(task_id, cycle_id)

    store = SQLiteStore(ws.root / "meridian_expert.db")
    store.init()
    rec = TaskRecord(
        task_id=task_id,
        state=TaskState.TRIAGED,
        family=TaskFamily.THEORY,
        created_at=datetime.utcnow(),
        current_cycle=cycle_id,
    )
    store.insert_task(rec)
    return store, ws, rec


def test_run_to_gate_flow_fake_backend(tmp_path: Path, monkeypatch) -> None:
    fixture = build_fixture_workspace(tmp_path)
    monkeypatch.setenv("MERIDIAN_REPO_PATH", str(fixture["meridian"]))
    monkeypatch.setenv("MERIDIAN_AUX_REPO_PATH", str(fixture["meridian_aux"]))

    store, ws, rec = _setup_task(tmp_path)
    brief = deterministic_triage_from_text("Explain analyzer internals with evidence")
    brief.needs_clarification = False

    result = run_task(
        rec,
        store,
        ws,
        brief,
        llm_client=_llm_client(),
        options=RunOptions(to_gate=True),
        lifecycle_stage="prototype",
        require_review=True,
    )

    assert result is None
    current = store.get_task(rec.task_id)
    assert current is not None
    assert current.state == TaskState.IN_REVIEW
    assert ws.artifact_paths(rec.task_id, rec.current_cycle, "prototype").answer_draft().exists()


def test_through_delivery_flow_fake_backend(tmp_path: Path, monkeypatch) -> None:
    fixture = build_fixture_workspace(tmp_path)
    monkeypatch.setenv("MERIDIAN_REPO_PATH", str(fixture["meridian"]))
    monkeypatch.setenv("MERIDIAN_AUX_REPO_PATH", str(fixture["meridian_aux"]))

    store, ws, rec = _setup_task(tmp_path)
    brief = deterministic_triage_from_text("Explain meridian model orchestration with evidence")

    delivered_path = run_task(
        rec,
        store,
        ws,
        brief,
        llm_client=_llm_client(),
        options=RunOptions(through_delivery=True, bypass_review_for_tests=True),
        lifecycle_stage="prototype",
        require_review=True,
    )

    assert delivered_path is not None
    assert Path(delivered_path).exists()
    current = store.get_task(rec.task_id)
    assert current is not None
    assert current.state == TaskState.DELIVERED


def test_missing_repo_blocker(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MERIDIAN_REPO_PATH", str(tmp_path / "missing-meridian"))
    monkeypatch.setenv("MERIDIAN_AUX_REPO_PATH", str(tmp_path / "missing-aux"))

    store, ws, rec = _setup_task(tmp_path)
    brief = deterministic_triage_from_text("Investigate update risk in predict.py")

    result = run_task(
        rec,
        store,
        ws,
        brief,
        llm_client=_llm_client(),
        options=RunOptions(to_gate=True),
        lifecycle_stage="prototype",
        require_review=True,
    )

    assert result is None
    current = store.get_task(rec.task_id)
    assert current is not None
    assert current.state == TaskState.BLOCKED
    blocker = ws.artifact_paths(rec.task_id, rec.current_cycle, "prototype").evidence_bundle().read_text(encoding="utf-8")
    assert "Investigation blocked" in blocker


def test_prototype_delivery_artifacts(tmp_path: Path, monkeypatch) -> None:
    fixture = build_fixture_workspace(tmp_path)
    monkeypatch.setenv("MERIDIAN_REPO_PATH", str(fixture["meridian"]))
    monkeypatch.setenv("MERIDIAN_AUX_REPO_PATH", str(fixture["meridian_aux"]))

    store, ws, rec = _setup_task(tmp_path)
    brief = deterministic_triage_from_text("How to use Analyzer with snippet and evidence")
    brief.needs_clarification = False
    brief.task_family = TaskFamily.USAGE
    rec.family = TaskFamily.USAGE
    store.conn.execute("update tasks set family=? where task_id=?", (TaskFamily.USAGE.value, rec.task_id))
    store.conn.commit()

    run_task(
        rec,
        store,
        ws,
        brief,
        llm_client=_llm_client(),
        options=RunOptions(through_delivery=True, bypass_review_for_tests=True),
        lifecycle_stage="prototype",
        require_review=True,
    )

    paths = ws.artifact_paths(rec.task_id, rec.current_cycle, "prototype")
    assert paths.delivery_answer().name == "answer.prototype.md"
    assert paths.delivery_manifest().name == "manifest.prototype.json"
    manifest_text = paths.delivery_manifest().read_text(encoding="utf-8")
    assert '"prototype": true' in manifest_text


def test_review_item_creation_without_duplicates_and_rerun(tmp_path: Path, monkeypatch) -> None:
    fixture = build_fixture_workspace(tmp_path)
    monkeypatch.setenv("MERIDIAN_REPO_PATH", str(fixture["meridian"]))
    monkeypatch.setenv("MERIDIAN_AUX_REPO_PATH", str(fixture["meridian_aux"]))

    store, ws, rec = _setup_task(tmp_path)
    brief = deterministic_triage_from_text("Explain analyzer internals with evidence")
    brief.needs_clarification = False

    run_task(
        rec,
        store,
        ws,
        brief,
        llm_client=_llm_client(),
        options=RunOptions(to_gate=True),
        lifecycle_stage="prototype",
        require_review=True,
    )
    run_task(
        rec,
        store,
        ws,
        brief,
        llm_client=_llm_client(),
        options=RunOptions(to_gate=True),
        lifecycle_stage="prototype",
        require_review=True,
    )

    rows = store.conn.execute("select kind, count(*) c from review_items group by kind order by kind").fetchall()
    counts = {row[0]: row[1] for row in rows}
    assert counts == {"draft": 1, "task_brief": 1}
