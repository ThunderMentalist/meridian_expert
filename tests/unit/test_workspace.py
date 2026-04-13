from pathlib import Path

from meridian_expert.storage.workspace import WorkspaceManager


def test_workspace_tree(tmp_path: Path):
    ws = WorkspaceManager(tmp_path)
    ws.ensure()
    ws.create_task_tree("T-20260413-0001", "C01")
    assert (tmp_path / "tasks/T-20260413-0001/input/task.md").parent.exists()
