from meridian_expert.enums import TaskState

ALLOWED = {
    TaskState.NEW: {TaskState.NEEDS_CLARIFICATION, TaskState.TRIAGED, TaskState.BLOCKED},
    TaskState.NEEDS_CLARIFICATION: {TaskState.TRIAGED, TaskState.BLOCKED},
    TaskState.TRIAGED: {TaskState.INVESTIGATING},
    TaskState.INVESTIGATING: {TaskState.DRAFT_READY, TaskState.BLOCKED},
    TaskState.DRAFT_READY: {TaskState.IN_REVIEW},
    TaskState.IN_REVIEW: {TaskState.DELIVERED, TaskState.BLOCKED},
    TaskState.DELIVERED: {TaskState.CLOSED},
    TaskState.BLOCKED: {TaskState.CLOSED},
    TaskState.CLOSED: set(),
}


def can_transition(src: TaskState, dst: TaskState) -> bool:
    return dst in ALLOWED[src]
