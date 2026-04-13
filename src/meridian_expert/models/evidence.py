from pydantic import BaseModel


class EvidenceItem(BaseModel):
    repo: str
    path: str
    anchor: str
    rationale: str
    bundle: str
    confidence: float = 0.7
    direct: bool = True
