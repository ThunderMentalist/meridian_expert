from pathlib import Path

import yaml


def mode_for(family: str) -> str:
    data = yaml.safe_load(Path("config/lifecycle_modes.yaml").read_text(encoding="utf-8"))
    return data.get(family, "prototype")
