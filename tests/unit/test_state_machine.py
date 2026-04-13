from meridian_expert.enums import TaskState
from meridian_expert.orchestration.state_machine import can_transition


def test_transition():
    assert can_transition(TaskState.NEW, TaskState.TRIAGED)
    assert not can_transition(TaskState.NEW, TaskState.DELIVERED)
