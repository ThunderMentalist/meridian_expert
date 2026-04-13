from pydantic import BaseModel


class CompatibilityFinding(BaseModel):
    upstream: str
    dependents: list[str]
    risk_level: str
    changed: bool
    notes: str = ""
