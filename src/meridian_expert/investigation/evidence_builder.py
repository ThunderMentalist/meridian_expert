from meridian_expert.models.evidence import EvidenceItem


def from_bundle(bundle: dict) -> list[EvidenceItem]:
    items=[]
    for p in bundle.get("files", []):
        repo = "meridian_aux" if p.startswith("meridian_aux/") else "meridian"
        items.append(EvidenceItem(repo=repo, path=p, anchor="file", rationale=f"Selected from bundle {bundle['name']}", bundle=bundle["name"]))
    return items
