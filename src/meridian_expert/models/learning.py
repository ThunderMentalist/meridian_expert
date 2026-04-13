from pydantic import BaseModel


class LearningCandidate(BaseModel):
    candidate_id: str
    task_id: str
    status: str = "pending"
    category: str = "candidate_learning"
