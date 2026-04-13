from __future__ import annotations

from pathlib import Path


class WorkspaceManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure(self) -> None:
        (self.root / "tasks").mkdir(parents=True, exist_ok=True)
        (self.root / "exports").mkdir(parents=True, exist_ok=True)
        (self.root / "exemplars").mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str) -> Path:
        return self.root / "tasks" / task_id

    def create_task_tree(self, task_id: str, cycle_id: str) -> Path:
        t = self.task_dir(task_id)
        for rel in [
            "input/attachments",
            f"cycles/{cycle_id}/triage",
            f"cycles/{cycle_id}/investigation",
            f"cycles/{cycle_id}/draft/snippets",
            f"cycles/{cycle_id}/review",
            "deliveries",
            "logs",
            f"cycles/{cycle_id}/prototype/triage",
            f"cycles/{cycle_id}/prototype/investigation",
            f"cycles/{cycle_id}/prototype/draft",
            "deliveries/prototype",
        ]:
            (t / rel).mkdir(parents=True, exist_ok=True)
        return t
