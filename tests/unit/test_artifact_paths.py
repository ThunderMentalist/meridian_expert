from pathlib import Path

from meridian_expert.storage.workspace import ArtifactPaths, WorkspaceManager


def test_artifact_paths_prototype() -> None:
    paths = ArtifactPaths(Path("/tmp/task"), cycle_id="C01", lifecycle_stage="prototype", delivery_id="D01")
    assert paths.task_brief().as_posix().endswith("cycles/C01/prototype/triage/task_brief.prototype.md")
    assert paths.evidence_bundle().as_posix().endswith("cycles/C01/prototype/investigation/evidence_bundle.prototype.md")
    assert paths.answer_draft().as_posix().endswith("cycles/C01/prototype/draft/answer_draft.prototype.md")
    assert paths.delivery_answer().as_posix().endswith("deliveries/prototype/D01/answer.prototype.md")
    assert paths.delivery_manifest().as_posix().endswith("deliveries/prototype/D01/manifest.prototype.json")


def test_artifact_paths_non_prototype() -> None:
    paths = ArtifactPaths(Path("/tmp/task"), cycle_id="C02", lifecycle_stage="mature", delivery_id="D03")
    assert paths.task_brief().as_posix().endswith("cycles/C02/triage/task_brief.md")
    assert paths.evidence_bundle().as_posix().endswith("cycles/C02/investigation/evidence_bundle.md")
    assert paths.answer_draft().as_posix().endswith("cycles/C02/draft/answer_draft.md")
    assert paths.delivery_answer().as_posix().endswith("deliveries/D03/answer.md")
    assert paths.delivery_manifest().as_posix().endswith("deliveries/D03/manifest.json")


def test_workspace_tree_includes_prototype_review(tmp_path: Path) -> None:
    ws = WorkspaceManager(tmp_path)
    ws.ensure()
    ws.create_task_tree("T-20260413-0001", "C01")
    assert (tmp_path / "tasks/T-20260413-0001/cycles/C01/prototype/review").exists()
