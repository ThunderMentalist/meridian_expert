from datetime import datetime

from meridian_expert.ids import cycle_id, delivery_id, task_id


def test_ids():
    assert task_id(datetime(2026, 4, 13), 1) == "T-20260413-0001"
    assert cycle_id(2) == "C02"
    assert delivery_id(3) == "D03"
