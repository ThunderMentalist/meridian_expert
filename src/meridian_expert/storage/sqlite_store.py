from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from meridian_expert.enums import TaskState
from meridian_expert.models.artifact import ArtifactRecord
from meridian_expert.models.review import ReviewItem
from meridian_expert.models.task import TaskRecord


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def init(self) -> None:
        cur = self.conn.cursor()
        cur.executescript("""
        create table if not exists tasks (
          task_id text primary key,
          state text not null,
          family text not null,
          created_at text not null,
          current_cycle text not null,
          parent_task_id text,
          related_task_id text,
          source_task_id text
        );
        create table if not exists task_cycles (task_id text, cycle_id text, primary key(task_id, cycle_id));
        create table if not exists deliveries (task_id text, delivery_id text, path text, primary key(task_id, delivery_id));
        create table if not exists artifacts (
          artifact_kind text,
          task_id text not null,
          cycle_id text,
          delivery_id text,
          relative_path text not null,
          lifecycle_stage text not null,
          reuse_policy text not null,
          eligible_for_learning integer not null,
          eligible_for_golden_promotion integer not null,
          created_at text not null
        );
        create table if not exists events (task_id text, event_ts text, event_type text, payload text);
        create table if not exists review_items (review_id text primary key, task_id text, cycle_id text, kind text, status text, created_at text);
        create table if not exists learning_candidates (candidate_id text primary key, task_id text, status text, category text);
        create table if not exists approved_learning (learning_id text primary key, payload text);
        create table if not exists compatibility_notes (note_id text primary key, task_id text, status text);
        create table if not exists exemplar_candidates (candidate_id text primary key, task_id text, status text);
        """)
        self._migrate_artifacts_table()
        self.conn.commit()

    def _migrate_artifacts_table(self) -> None:
        rows = self.conn.execute("pragma table_info(artifacts)").fetchall()
        existing = {row[1] for row in rows}
        required: dict[str, str] = {
            "artifact_kind": "text",
            "task_id": "text",
            "cycle_id": "text",
            "delivery_id": "text",
            "relative_path": "text",
            "lifecycle_stage": "text",
            "reuse_policy": "text",
            "eligible_for_learning": "integer",
            "eligible_for_golden_promotion": "integer",
            "created_at": "text",
        }
        for column, column_type in required.items():
            if column not in existing:
                self.conn.execute(f"alter table artifacts add column {column} {column_type}")

    def insert_task(self, rec: TaskRecord) -> None:
        self.conn.execute(
            "insert into tasks values (?,?,?,?,?,?,?,?)",
            (rec.task_id, rec.state.value, rec.family.value, rec.created_at.isoformat(), rec.current_cycle, rec.parent_task_id, rec.related_task_id, rec.source_task_id),
        )
        self.conn.execute("insert or ignore into task_cycles values (?,?)", (rec.task_id, rec.current_cycle))
        self.conn.commit()

    def insert_artifact(self, rec: ArtifactRecord) -> None:
        self.conn.execute(
            """
            insert into artifacts (
              artifact_kind, task_id, cycle_id, delivery_id, relative_path,
              lifecycle_stage, reuse_policy, eligible_for_learning,
              eligible_for_golden_promotion, created_at
            ) values (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                rec.artifact_kind,
                rec.task_id,
                rec.cycle_id,
                rec.delivery_id,
                rec.relative_path,
                rec.lifecycle_stage,
                rec.reuse_policy,
                int(rec.eligible_for_learning),
                int(rec.eligible_for_golden_promotion),
                rec.created_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get_task(self, task_id: str) -> TaskRecord | None:
        row = self.conn.execute("select * from tasks where task_id=?", (task_id,)).fetchone()
        if not row:
            return None
        return TaskRecord(
            task_id=row["task_id"],
            state=TaskState(row["state"]),
            family=row["family"],
            created_at=datetime.fromisoformat(row["created_at"]),
            current_cycle=row["current_cycle"],
            parent_task_id=row["parent_task_id"],
            related_task_id=row["related_task_id"],
            source_task_id=row["source_task_id"],
        )

    def update_state(self, task_id: str, state: TaskState) -> None:
        self.conn.execute("update tasks set state=? where task_id=?", (state.value, task_id))
        self.conn.commit()

    def create_review_item(self, item: ReviewItem) -> None:
        self.conn.execute(
            "insert into review_items values (?,?,?,?,?,?)",
            (item.review_id, item.task_id, item.cycle_id, item.kind, item.status, item.created_at.isoformat()),
        )
        self.conn.commit()

    def list_review_items(self, status: str = "pending") -> list[sqlite3.Row]:
        return list(self.conn.execute("select * from review_items where status=? order by created_at", (status,)).fetchall())

    def set_review_status(self, review_id: str, status: str) -> None:
        self.conn.execute("update review_items set status=? where review_id=?", (status, review_id))
        self.conn.commit()
