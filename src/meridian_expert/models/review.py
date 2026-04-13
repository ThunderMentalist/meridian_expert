from datetime import datetime

from pydantic import BaseModel


class ReviewItem(BaseModel):
    review_id: str
    task_id: str
    cycle_id: str
    kind: str
    status: str = "pending"
    created_at: datetime
