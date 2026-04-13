from datetime import datetime


def task_id(now: datetime, sequence: int) -> str:
    return f"T-{now.strftime('%Y%m%d')}-{sequence:04d}"


def cycle_id(n: int) -> str:
    return f"C{n:02d}"


def delivery_id(n: int) -> str:
    return f"D{n:02d}"
