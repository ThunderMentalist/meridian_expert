from pathlib import Path


def load_prompt(name: str) -> str:
    return (Path(__file__).resolve().parent.parent / "prompt_specs" / f"{name}.md").read_text(encoding="utf-8")
