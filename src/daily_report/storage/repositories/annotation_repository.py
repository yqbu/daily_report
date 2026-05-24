from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

SOURCE_TYPES = {'app', 'browser', 'clipboard', 'ai_prompt'}


class AnnotationRepository:
    """Repository for user annotations shared by all source tables."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def update_annotation(
        self,
        source_type: str,
        source_id: int,
        category: str | None = None,
        note: str | None = None,
        importance: int | None = None,
    ) -> sqlite3.Row:
        self._validate_source_type(source_type)
        existing = self.get_annotation(source_type, source_id)
        now = _now()

        if existing is None:
            self.conn.execute(
                """
                INSERT INTO entry_annotations (
                    source_type, source_id, category, note, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_type,
                    int(source_id),
                    category,
                    note,
                    int(importance if importance is not None else 0),
                    now,
                    now,
                ),
            )
        else:
            self.conn.execute(
                """
                UPDATE entry_annotations
                SET category = COALESCE(?, category),
                    note = COALESCE(?, note),
                    importance = COALESCE(?, importance),
                    updated_at = ?
                WHERE source_type = ? AND source_id = ?
                """,
                (
                    category,
                    note,
                    int(importance) if importance is not None else None,
                    now,
                    source_type,
                    int(source_id),
                ),
            )
        self.conn.commit()
        row = self.get_annotation(source_type, source_id)
        if row is None:
            raise RuntimeError(f'Failed to update annotation: {source_type}:{source_id}')
        return row

    def get_annotation(self, source_type: str, source_id: int) -> sqlite3.Row | None:
        self._validate_source_type(source_type)
        return self.conn.execute(
            """
            SELECT *
            FROM entry_annotations
            WHERE source_type = ? AND source_id = ?
            """,
            (source_type, int(source_id)),
        ).fetchone()

    def get_annotations_for_ids(
        self,
        source_type: str,
        source_ids: list[int],
    ) -> dict[int, dict[str, Any]]:
        self._validate_source_type(source_type)
        if not source_ids:
            return {}
        placeholders = ','.join('?' for _ in source_ids)
        rows = self.conn.execute(
            f"""
            SELECT *
            FROM entry_annotations
            WHERE source_type = ? AND source_id IN ({placeholders})
            """,
            tuple([source_type, *[int(source_id) for source_id in source_ids]]),
        ).fetchall()
        return {int(row['source_id']): dict(row) for row in rows}

    @staticmethod
    def _validate_source_type(source_type: str) -> None:
        if source_type not in SOURCE_TYPES:
            raise ValueError(f'Unsupported annotation source_type: {source_type}')


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
