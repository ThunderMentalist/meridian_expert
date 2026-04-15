from pathlib import Path

from meridian_expert.models.artifact import ArtifactRecord
from meridian_expert.storage.sqlite_store import SQLiteStore


def test_insert_artifact_prototype_defaults(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "store.db")
    store.init()
    rec = ArtifactRecord.for_stage(
        artifact_kind="answer_draft",
        task_id="T-20260415-0001",
        cycle_id="C01",
        relative_path="cycles/C01/prototype/draft/answer_draft.prototype.md",
        lifecycle_stage="prototype",
    )
    store.insert_artifact(rec)

    row = store.conn.execute("select * from artifacts where task_id=?", ("T-20260415-0001",)).fetchone()
    assert row is not None
    assert row["artifact_kind"] == "answer_draft"
    assert row["lifecycle_stage"] == "prototype"
    assert row["reuse_policy"] == "blocked"
    assert row["eligible_for_learning"] == 0
    assert row["eligible_for_golden_promotion"] == 0


def test_insert_artifact_mature_defaults(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "store.db")
    store.init()
    rec = ArtifactRecord.for_stage(
        artifact_kind="delivery_manifest",
        task_id="T-20260415-0002",
        cycle_id="C01",
        delivery_id="D01",
        relative_path="deliveries/D01/manifest.json",
        lifecycle_stage="mature",
    )
    store.insert_artifact(rec)

    row = store.conn.execute("select * from artifacts where task_id=?", ("T-20260415-0002",)).fetchone()
    assert row["reuse_policy"] == "allowed"
    assert row["eligible_for_learning"] == 1
    assert row["eligible_for_golden_promotion"] == 1
