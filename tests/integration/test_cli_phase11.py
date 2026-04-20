from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from meridian_expert.cli import app
from meridian_expert.storage.sqlite_store import SQLiteStore
from meridian_expert.testing_support.repo_fixtures import build_fixture_workspace


runner = CliRunner()


def _create_task_markdown(tmp_path: Path, text: str = "Explain analyzer internals in meridian/analysis/analyzer.py with evidence") -> Path:
    task_md = tmp_path / "task.md"
    task_md.write_text(f"# Task\n\n{text}\n", encoding="utf-8")
    return task_md


def _env(tmp_path: Path) -> dict[str, str]:
    fixture = build_fixture_workspace(tmp_path)
    workspace = tmp_path / "runtime"
    return {
        "MERIDIAN_REPO_PATH": str(fixture["meridian"]),
        "MERIDIAN_AUX_REPO_PATH": str(fixture["meridian_aux"]),
        "MERIDIAN_EXPERT_WORKSPACE": str(workspace),
        "MERIDIAN_EXPERT_LLM_BACKEND": "fake",
    }


def _create_task(tmp_path: Path, env: dict[str, str], text: str = "Explain analyzer internals in meridian/analysis/analyzer.py with evidence") -> str:
    res = runner.invoke(app, ["task", "create", str(_create_task_markdown(tmp_path, text))], env=env)
    assert res.exit_code == 0
    return res.stdout.strip()


def test_cli_smoke_major_commands(tmp_path: Path) -> None:
    env = _env(tmp_path)
    task_id = _create_task(tmp_path, env)
    assert runner.invoke(app, ["doctor"], env=env).exit_code == 0
    assert runner.invoke(app, ["task", "status", task_id], env=env).exit_code == 0
    assert runner.invoke(app, ["task", "show", task_id, "--evidence-summary"], env=env).exit_code == 0
    assert runner.invoke(app, ["task", "clarify", task_id, "clear now"], env=env).exit_code == 0
    assert runner.invoke(app, ["task", "run", task_id, "--to-gate"], env=env).exit_code == 0
    assert runner.invoke(app, ["review", "queue", "--status", "all", "--task-id", task_id], env=env).exit_code == 0
    assert runner.invoke(app, ["compat", "check", "--changed-file", "src/meridian_aux/nest/nest.py"], env=env).exit_code == 0
    assert runner.invoke(app, ["bundle", "list"], env=env).exit_code == 0


def test_duplicate_review_item_prevention_on_rerun(tmp_path: Path) -> None:
    env = _env(tmp_path)
    task_id = _create_task(tmp_path, env)

    assert runner.invoke(app, ["task", "run", task_id, "--to-gate"], env=env).exit_code == 0
    assert runner.invoke(app, ["task", "run", task_id, "--to-gate"], env=env).exit_code == 0

    queue = runner.invoke(app, ["review", "queue", "--status", "all", "--task-id", task_id], env=env)
    items = json.loads(queue.stdout)
    kinds = [item["kind"] for item in items]
    assert sorted(kinds) == ["draft", "task_brief"]


def test_review_approval_gates_delivery(tmp_path: Path) -> None:
    env = _env(tmp_path)
    task_id = _create_task(tmp_path, env)

    assert runner.invoke(app, ["task", "run", task_id, "--to-gate"], env=env).exit_code == 0

    blocked = runner.invoke(app, ["task", "run", task_id, "--through-delivery"], env=env)
    assert blocked.exit_code != 0

    queue = runner.invoke(app, ["review", "queue", "--status", "pending", "--task-id", task_id], env=env)
    items = json.loads(queue.stdout)
    for item in items:
        decision = runner.invoke(app, ["review", "decide", item["review_id"], "approve"], env=env)
        assert decision.exit_code == 0

    delivered = runner.invoke(app, ["task", "run", task_id, "--through-delivery"], env=env)
    assert delivered.exit_code == 0
    assert "answer.prototype.md" in delivered.stdout


def test_same_task_redirection_vs_follow_on_creation(tmp_path: Path) -> None:
    env = _env(tmp_path)
    task_id = _create_task(tmp_path, env)

    redirect = runner.invoke(app, ["task", "redirect", task_id, "adjust scope", "--new-cycle"], env=env)
    assert redirect.exit_code == 0

    workspace = Path(env["MERIDIAN_EXPERT_WORKSPACE"])
    store = SQLiteStore(workspace / "meridian_expert.db")
    rec = store.get_task(task_id)
    assert rec is not None
    assert rec.current_cycle == "C02"

    assert runner.invoke(app, ["task", "run", task_id, "--to-gate"], env=env).exit_code == 0
    queue = json.loads(runner.invoke(app, ["review", "queue", "--status", "pending", "--task-id", task_id], env=env).stdout)
    for item in queue:
        assert runner.invoke(app, ["review", "decide", item["review_id"], "approve"], env=env).exit_code == 0
    assert runner.invoke(app, ["task", "run", task_id, "--through-delivery"], env=env).exit_code == 0

    follow_task_md = _create_task_markdown(tmp_path, text="Follow up task for delivery")
    follow_on = runner.invoke(app, ["task", "follow-on", task_id, str(follow_task_md)], env=env)
    assert follow_on.exit_code == 0
    child_task_id = follow_on.stdout.strip()
    child = store.get_task(child_task_id)
    assert child is not None
    assert child.parent_task_id == task_id
    assert child.related_task_id == task_id


def test_prototype_excluded_from_learning_and_exemplar(tmp_path: Path) -> None:
    env = _env(tmp_path)
    task_id = _create_task(tmp_path, env)

    assert runner.invoke(app, ["task", "run", task_id, "--to-gate"], env=env).exit_code == 0
    queue = json.loads(runner.invoke(app, ["review", "queue", "--status", "pending", "--task-id", task_id], env=env).stdout)
    for item in queue:
        assert runner.invoke(app, ["review", "decide", item["review_id"], "approve"], env=env).exit_code == 0
    assert runner.invoke(app, ["task", "run", task_id, "--through-delivery"], env=env).exit_code == 0

    learning_nom = runner.invoke(app, ["learning", "nominate", task_id], env=env)
    exemplar_nom = runner.invoke(app, ["exemplar", "nominate", task_id], env=env)
    assert learning_nom.exit_code != 0
    assert exemplar_nom.exit_code != 0


def test_evidence_summary_display_contains_required_fields(tmp_path: Path) -> None:
    env = _env(tmp_path)
    task_id = _create_task(tmp_path, env, text="Review src/meridian_aux/nest/nest.py decomposition risk")
    show = runner.invoke(app, ["task", "show", task_id, "--evidence-summary"], env=env)
    assert show.exit_code == 0
    payload = json.loads(show.stdout)

    summary = payload["evidence_summary"]
    assert "selected_anchors" in summary
    assert "selected_bundles" in summary
    assert "selected_tests" in summary
    assert "cross_repo_route" in summary
    assert "hotspot_tier" in summary
    assert "dependency_mode" in summary
    assert "compat_shim_warning" in summary
    assert "under_tested_warning" in summary


def test_learning_and_exemplar_list_and_decide_flows(tmp_path: Path) -> None:
    env = _env(tmp_path)
    task_id = _create_task(tmp_path, env)

    workspace = Path(env["MERIDIAN_EXPERT_WORKSPACE"])
    store = SQLiteStore(workspace / "meridian_expert.db")
    store.init()
    store.create_learning_candidate(f"LC-{task_id}", task_id)
    store.create_exemplar_candidate(f"EC-{task_id}", task_id)

    learning_list = runner.invoke(app, ["learning", "list", "--status", "pending"], env=env)
    exemplar_list = runner.invoke(app, ["exemplar", "list", "--status", "pending"], env=env)
    assert learning_list.exit_code == 0
    assert exemplar_list.exit_code == 0
    assert f"LC-{task_id}" in learning_list.stdout
    assert f"EC-{task_id}" in exemplar_list.stdout

    assert runner.invoke(app, ["learning", "decide", f"LC-{task_id}", "approve"], env=env).exit_code == 0
    assert runner.invoke(app, ["exemplar", "decide", f"EC-{task_id}", "reject"], env=env).exit_code == 0

    approved_learning = runner.invoke(app, ["learning", "list", "--status", "approved"], env=env)
    rejected_exemplar = runner.invoke(app, ["exemplar", "list", "--status", "rejected"], env=env)
    assert f"LC-{task_id}" in approved_learning.stdout
    assert f"EC-{task_id}" in rejected_exemplar.stdout


def test_clarification_unblocks_direct_request_and_reaches_gate(tmp_path: Path) -> None:
    env = _env(tmp_path)
    create_text = "Identify the Bayesian MCMC algorithm that samples the posterior and list what the default hyper-parameters are."
    clarify_text = (
        "In the core Meridian repo, identify the Bayesian MCMC algorithm used to sample the posterior and list the default "
        "sampler hyper-parameters. Focus on Meridian itself, not meridian_aux."
    )

    task_id = _create_task(tmp_path, env, text=create_text)

    created_status = runner.invoke(app, ["task", "status", task_id], env=env)
    assert created_status.exit_code == 0
    assert json.loads(created_status.stdout)["state"] == "NEEDS_CLARIFICATION"

    clarified = runner.invoke(app, ["task", "clarify", task_id, clarify_text], env=env)
    assert clarified.exit_code == 0

    clarified_status = runner.invoke(app, ["task", "status", task_id], env=env)
    assert clarified_status.exit_code == 0
    assert json.loads(clarified_status.stdout)["state"] == "TRIAGED"

    ran = runner.invoke(app, ["task", "run", task_id, "--to-gate"], env=env)
    assert ran.exit_code == 0

    queue = runner.invoke(app, ["review", "queue", "--status", "all", "--task-id", task_id], env=env)
    assert queue.exit_code == 0
    kinds = sorted(item["kind"] for item in json.loads(queue.stdout))
    assert kinds == ["draft", "task_brief"]

    workspace = Path(env["MERIDIAN_EXPERT_WORKSPACE"])
    draft = workspace / "tasks" / task_id / "cycles" / "C01" / "prototype" / "draft" / "answer_draft.prototype.md"
    assert draft.exists()
