from pydantic import BaseModel


class ArtifactRecord(BaseModel):
    task_id: str
    cycle_id: str
    kind: str
    path: str
    lifecycle_stage: str
    reuse_policy: str = "allowed"
