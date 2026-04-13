from enum import Enum


class TaskFamily(str, Enum):
    THEORY = "theory"
    USAGE = "usage"
    UPDATES = "updates"
    BUILDER = "builder"


class TaskState(str, Enum):
    NEW = "NEW"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    DRAFT_READY = "DRAFT_READY"
    IN_REVIEW = "IN_REVIEW"
    DELIVERED = "DELIVERED"
    BLOCKED = "BLOCKED"
    CLOSED = "CLOSED"


class LifecycleMode(str, Enum):
    PROTOTYPE = "prototype"
    WARM_UP = "warm_up"
    MATURE = "mature"
    SHOCK = "shock"
