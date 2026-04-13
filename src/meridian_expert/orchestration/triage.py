from meridian_expert.enums import TaskFamily
from meridian_expert.models.task import TaskBrief


def triage_from_text(text: str) -> TaskBrief:
    lower = text.lower()
    family = TaskFamily.THEORY
    if any(k in lower for k in ["how do i use", "snippet", "example"]):
        family = TaskFamily.USAGE
    if any(k in lower for k in ["impact", "compatibility", "update", "risk"]):
        family = TaskFamily.UPDATES
    return TaskBrief(title=text.splitlines()[0][:80], task_family=family, goal=text[:400], snippets_allowed=family==TaskFamily.USAGE, unknowns=[] if len(text)>20 else ["Task underspecified"])
