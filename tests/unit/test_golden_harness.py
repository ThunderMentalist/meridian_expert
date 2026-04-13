from pathlib import Path
import yaml


def test_golden_cases_exist():
    base = Path("tests/golden_tasks/cases")
    cases = [p for p in base.iterdir() if p.is_dir()]
    assert len(cases) >= 8
    for c in cases:
        assert (c / "task.md").exists()
        data = yaml.safe_load((c / "expected.yaml").read_text())
        assert "expected_family" in data
