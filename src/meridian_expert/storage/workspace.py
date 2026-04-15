from __future__ import annotations

from pathlib import Path


class ArtifactPaths:
    def __init__(self, task_dir: Path, cycle_id: str, lifecycle_stage: str, delivery_id: str = "D01") -> None:
        self.task_dir = task_dir
        self.cycle_id = cycle_id
        self.lifecycle_stage = lifecycle_stage
        self.delivery_id = delivery_id

    @property
    def _is_prototype(self) -> bool:
        return self.lifecycle_stage == "prototype"

    @property
    def _cycle_root(self) -> Path:
        base = self.task_dir / "cycles" / self.cycle_id
        if self._is_prototype:
            return base / "prototype"
        return base

    @property
    def _delivery_root(self) -> Path:
        if self._is_prototype:
            return self.task_dir / "deliveries" / "prototype" / self.delivery_id
        return self.task_dir / "deliveries" / self.delivery_id

    def task_brief(self) -> Path:
        name = "task_brief.prototype.md" if self._is_prototype else "task_brief.md"
        return self._cycle_root / "triage" / name

    def clarification_request(self) -> Path:
        name = "clarification_request.prototype.md" if self._is_prototype else "clarification_request.md"
        return self._cycle_root / "triage" / name

    def clarifications(self) -> Path:
        name = "clarifications.prototype.md" if self._is_prototype else "clarifications.md"
        return self._cycle_root / "triage" / name

    def evidence_bundle(self) -> Path:
        name = "evidence_bundle.prototype.md" if self._is_prototype else "evidence_bundle.md"
        return self._cycle_root / "investigation" / name

    def answer_draft(self) -> Path:
        name = "answer_draft.prototype.md" if self._is_prototype else "answer_draft.md"
        return self._cycle_root / "draft" / name

    def appendix_draft(self) -> Path:
        name = "appendix_draft.prototype.md" if self._is_prototype else "appendix_draft.md"
        return self._cycle_root / "draft" / name

    def review_notes(self) -> Path:
        name = "review_notes.prototype.md" if self._is_prototype else "review_notes.md"
        return self._cycle_root / "review" / name

    def decision_json(self) -> Path:
        name = "decision.prototype.json" if self._is_prototype else "decision.json"
        return self._cycle_root / "review" / name

    def delivery_answer(self) -> Path:
        name = "answer.prototype.md" if self._is_prototype else "answer.md"
        return self._delivery_root / name

    def delivery_appendix(self) -> Path:
        name = "appendix.prototype.md" if self._is_prototype else "appendix.md"
        return self._delivery_root / name

    def delivery_manifest(self) -> Path:
        name = "manifest.prototype.json" if self._is_prototype else "manifest.json"
        return self._delivery_root / name


class WorkspaceManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure(self) -> None:
        (self.root / "tasks").mkdir(parents=True, exist_ok=True)
        (self.root / "exports").mkdir(parents=True, exist_ok=True)
        (self.root / "exemplars").mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str) -> Path:
        return self.root / "tasks" / task_id

    def artifact_paths(self, task_id: str, cycle_id: str, lifecycle_stage: str, delivery_id: str = "D01") -> ArtifactPaths:
        return ArtifactPaths(
            task_dir=self.task_dir(task_id),
            cycle_id=cycle_id,
            lifecycle_stage=lifecycle_stage,
            delivery_id=delivery_id,
        )

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
            f"cycles/{cycle_id}/prototype/review",
            "deliveries/prototype",
        ]:
            (t / rel).mkdir(parents=True, exist_ok=True)
        return t
