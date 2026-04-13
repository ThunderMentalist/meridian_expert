from pathlib import Path

import yaml


def load_profiles(path: Path = Path("config/model_profiles.yaml")) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
