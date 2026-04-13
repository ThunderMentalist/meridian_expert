from datetime import datetime

from meridian_expert.models.review import ReviewItem


def make_item(task_id: str, cycle_id: str, kind: str) -> ReviewItem:
    return ReviewItem(review_id=f"R-{task_id}-{cycle_id}-{kind}", task_id=task_id, cycle_id=cycle_id, kind=kind, created_at=datetime.utcnow())
