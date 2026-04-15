from __future__ import annotations

from pathlib import Path


def _write(root: Path, relative_path: str, body: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.strip() + "\n", encoding="utf-8")


def build_fixture_meridian_repo(root: Path) -> Path:
    repo = root / "meridian"
    repo.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {
        "meridian/analysis/analyzer.py": '''"""Analyzer façade."""
from meridian.model import model
from meridian.analysis import visualizer
from meridian.analysis import summary_text

class Analyzer:
    def run(self) -> model.Meridian:
        return model.Meridian()
''',
        "meridian/analysis/optimizer.py": "from meridian.analysis import analyzer\n",
        "meridian/analysis/visualizer.py": "from meridian.data import input_data\nclass MediaSummary: ...\n",
        "meridian/analysis/summary_text.py": "from meridian.analysis import visualizer\n",
        "meridian/model/model.py": '''"""Model orchestrator."""
from meridian.model import equations, adstock_hill, transformers, spec
from meridian.model import context
from meridian.data import input_data

class Meridian:
    def fit(self, data: input_data.InputData) -> None:
        _ = (equations, adstock_hill, transformers, spec, context, data)
''',
        "meridian/model/context.py": "from meridian.model import media\n",
        "meridian/model/equations.py": "def calculate(x: float) -> float:\n    return x\n",
        "meridian/model/adstock_hill.py": "from meridian.model import equations\n",
        "meridian/model/transformers.py": "from meridian.model import equations\n",
        "meridian/model/spec.py": "from meridian.constants import VERSION\n",
        "meridian/model/prior_distribution.py": "from meridian.model import spec\n",
        "meridian/model/prior_sampler.py": "from meridian.model import prior_distribution\n",
        "meridian/model/posterior_sampler.py": "from meridian.model import model\n",
        "meridian/model/media.py": "from meridian.model import knots\n",
        "meridian/model/knots.py": "def knot_count() -> int:\n    return 0\n",
        "meridian/model/eda/eda_engine.py": "from meridian.model.eda import eda_spec, eda_outcome\n",
        "meridian/model/eda/eda_outcome.py": "class EdaOutcome: ...\n",
        "meridian/model/eda/eda_spec.py": "class EdaSpec: ...\n",
        "meridian/data/input_data.py": "from meridian.data import time_coordinates\nclass InputData: ...\n",
        "meridian/data/time_coordinates.py": "class TimeCoordinates: ...\n",
        "meridian/constants.py": "VERSION = '0.0'\n",
        "meridian/backend/__init__.py": "from meridian.model import model\n",
        "meridian/templates/formatter.py": "from meridian.analysis import summary_text\n",
        "schema.py": "from meridian import constants\n",
        "scenarioplanner/mmm_ui_proto_generator.py": "from meridian.analysis import analyzer\n",
    }
    for path, body in files.items():
        _write(repo, path, body)

    return repo


def build_fixture_meridian_aux_repo(root: Path) -> Path:
    repo = root / "meridian_aux"
    repo.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {
        "src/meridian_aux/contribution/control_contribution.py": '''from meridian.analysis.analyzer import Analyzer
from meridian_aux.dashboard import nordic_client

def build_control(analyzer: Analyzer) -> str:
    return nordic_client.client_name(analyzer)
''',
        "src/meridian_aux/predict/predict.py": '''from meridian.model.model import Meridian
from meridian_aux.contribution import control_contribution

class Predictor:
    def predict(self, model: Meridian) -> str:
        return control_contribution.build_control(model)  # type: ignore[arg-type]
''',
        "src/meridian_aux/charts/transformed.py": "from meridian_aux.predict import predict\n",
        "src/meridian_aux/dashboard/nordic_client.py": "def client_name(_obj: object) -> str:\n    return 'nordic'\n",
        "src/meridian_aux/diagnostics/multicollinearity.py": "from meridian.analysis.analyzer import Analyzer\n",
        "src/meridian_aux/nest/nest.py": "from meridian_aux.predict import predict\n",
        "src/meridian_aux/optimization/roi.py": "from meridian_aux.predict import predict\n",
        "src/meridian_aux/diagnostics/residuals.py": "from meridian_aux.data import actuals_vs_fitted\n",
        "src/meridian_aux/data/actuals_vs_fitted.py": "from meridian_aux.data import curves\n",
        "src/meridian_aux/data/curves.py": "def curve() -> int:\n    return 1\n",
        "src/meridian_aux/contribution/media_contribution.py": "from meridian.analysis.visualizer import MediaSummary\n",
        "src/meridian_aux/study/iterate.py": "from meridian_aux.optimization import roi\n",
        "src/meridian_aux/charts/coefficients.py": "from meridian_aux.charts import transformed\n",
        "src/meridian_aux/diagnostics/tstats.py": "from meridian_aux.diagnostics import mass\n",
        "src/meridian_aux/diagnostics/mass.py": "from meridian_aux.predict import predict\n",
        "tests/test_nest_nest.py": "def test_placeholder() -> None:\n    assert True\n",
    }
    for path, body in files.items():
        _write(repo, path, body)

    return repo


def build_fixture_workspace(root: Path) -> dict[str, Path]:
    meridian = build_fixture_meridian_repo(root)
    meridian_aux = build_fixture_meridian_aux_repo(root)
    return {"meridian": meridian, "meridian_aux": meridian_aux}
