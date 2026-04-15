from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ArtifactRecord(BaseModel):
    artifact_kind: str
    task_id: str
    cycle_id: str | None = None
    delivery_id: str | None = None
    relative_path: str
    lifecycle_stage: str = "mature"
    reuse_policy: str = "allowed"
    eligible_for_learning: bool = True
    eligible_for_golden_promotion: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def for_stage(
        cls,
        *,
        artifact_kind: str,
        task_id: str,
        relative_path: str,
        lifecycle_stage: str,
        cycle_id: str | None = None,
        delivery_id: str | None = None,
    ) -> "ArtifactRecord":
        is_prototype = lifecycle_stage == "prototype"
        return cls(
            artifact_kind=artifact_kind,
            task_id=task_id,
            cycle_id=cycle_id,
            delivery_id=delivery_id,
            relative_path=relative_path,
            lifecycle_stage=lifecycle_stage,
            reuse_policy="blocked" if is_prototype else "allowed",
            eligible_for_learning=False if is_prototype else True,
            eligible_for_golden_promotion=False if is_prototype else True,
        )
