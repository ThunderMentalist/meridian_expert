def nominate_allowed(lifecycle_stage: str) -> bool:
    return lifecycle_stage != "prototype"
