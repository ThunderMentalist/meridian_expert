from typer.testing import CliRunner

from meridian_expert.cli import app


def test_doctor_runs():
    runner = CliRunner()
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
