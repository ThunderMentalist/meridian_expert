from __future__ import annotations

from datetime import datetime

from meridian_expert.enums import TaskFamily, TaskState
from meridian_expert.models.evidence import EvidenceItem, EvidencePack
from meridian_expert.models.task import TaskRecord
from meridian_expert.orchestration.runner import DraftOutput, persist_draft_stage
from meridian_expert.storage.sqlite_store import SQLiteStore
from meridian_expert.storage.workspace import WorkspaceManager
from meridian_expert.task_families.usage import generate_answer


def _pack(*paths: str) -> EvidencePack:
    return EvidencePack(
        anchor_files=[paths[0]] if paths else [],
        items=[
            EvidenceItem(
                repo_name="meridian_aux" if path.startswith("src/meridian_aux/") else "meridian",
                path=path,
                rationale="fixture evidence",
                authority_rank=8,
                significance=0.8,
                direct=True,
            )
            for path in paths
        ],
    )


def test_usage_api_question_produces_explanation_and_snippet() -> None:
    answer, snippets = generate_answer(
        "How do I use predict.py with Meridian model objects?",
        _pack("src/meridian_aux/predict/predict.py"),
    )

    assert "Usage guidance" in answer
    assert "do not invent" in answer.lower()
    assert snippets
    assert "from meridian.model.model import Meridian" in snippets[0]


def test_usage_predict_references_required_meridian_surfaces() -> None:
    answer, _ = generate_answer(
        "Help with src/meridian_aux/predict/predict.py",
        _pack("src/meridian_aux/predict/predict.py"),
    )

    assert "meridian/model/model.py" in answer
    assert "meridian/model/adstock_hill.py" in answer
    assert "meridian/model/transformers.py" in answer
    assert "meridian/model/equations.py" in answer
    assert "meridian/data/input_data.py" in answer


def test_snippet_artifact_saved_with_canonical_name_and_valid_syntax(tmp_path) -> None:
    ws = WorkspaceManager(tmp_path / "runtime")
    ws.ensure()
    task_id = "T-20260415-usage"
    cycle_id = "C01"
    ws.create_task_tree(task_id, cycle_id)

    store = SQLiteStore(ws.root / "meridian_expert.db")
    store.init()
    task = TaskRecord(
        task_id=task_id,
        state=TaskState.TRIAGED,
        family=TaskFamily.USAGE,
        created_at=datetime.utcnow(),
        current_cycle=cycle_id,
    )
    store.insert_task(task)

    _, snippets = generate_answer("How to use predict.py", _pack("src/meridian_aux/predict/predict.py"))
    draft = DraftOutput(answer_markdown="ok", snippets=snippets)
    persist_draft_stage(task, store, ws, draft, lifecycle_stage="prototype")

    snippet_path = ws.task_dir(task_id) / f"cycles/{cycle_id}/prototype/draft/snippets/example_01.py"
    assert snippet_path.exists()

    source = snippet_path.read_text(encoding="utf-8")
    compile(source, str(snippet_path), "exec")


def test_usage_avoids_nonexistent_api_when_not_supported_by_evidence() -> None:
    answer, snippets = generate_answer("How do I call meridian.magic_predict()?", evidence_pack=None)

    assert "unverified" in answer.lower() or "sparse" in answer.lower()
    assert snippets == []


def test_usage_attachment_aware_path() -> None:
    attachment = [
        "from meridian.analysis.analyzer import Analyzer\n"
        "analyzer = Analyzer()\n"
        "# existing predict flow\n"
    ]
    answer, snippets = generate_answer(
        "How to use predict.py from my current code?",
        _pack("src/meridian_aux/predict/predict.py"),
        attachment_texts=attachment,
    )

    assert "attachment" in answer.lower()
    assert snippets
    assert "reuse your existing Analyzer instance" in snippets[0]
