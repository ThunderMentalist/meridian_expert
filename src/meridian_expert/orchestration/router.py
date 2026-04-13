from meridian_expert.enums import TaskFamily


def route_family(explicit: str | None, triaged: TaskFamily, builder_enabled: bool = False) -> TaskFamily:
    if explicit:
        fam = TaskFamily(explicit)
        if fam == TaskFamily.BUILDER and not builder_enabled:
            raise ValueError("Builder family is disabled")
        return fam
    if triaged == TaskFamily.BUILDER and not builder_enabled:
        return TaskFamily.THEORY
    return triaged
