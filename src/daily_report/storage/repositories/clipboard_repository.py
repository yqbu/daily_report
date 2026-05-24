from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Any


class ClipboardEntryRepository:
    """Repository for clipboard text entries."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def upsert_entry(
        self,
        *,
        date: str,
        first_seen_at: datetime,
        last_seen_at: datetime,
        content: str,
        content_preview: str,
        content_hash: str,
        char_count: int,
        is_sensitive: bool,
        sensitivity_reason: str | None,
        is_selected: bool,
    ) -> int:
        now = _now()
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO clipboard_entries (
                    date, first_seen_at, last_seen_at, content, content_preview,
                    content_hash, char_count, is_sensitive, sensitivity_reason,
                    is_selected, is_deleted, seen_count, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?)
                ON CONFLICT(date, content_hash)
                DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    seen_count = clipboard_entries.seen_count + 1,
                    updated_at = excluded.updated_at
                """,
                (
                    date,
                    first_seen_at.isoformat(timespec='seconds'),
                    last_seen_at.isoformat(timespec='seconds'),
                    content,
                    content_preview,
                    content_hash,
                    int(char_count),
                    int(is_sensitive),
                    sensitivity_reason,
                    int(is_selected),
                    now,
                    now,
                ),
            )
            row = self.conn.execute(
                """
                SELECT id
                FROM clipboard_entries
                WHERE date = ? AND content_hash = ?
                """,
                (date, content_hash),
            ).fetchone()
            self.conn.commit()
        if row is None:
            raise RuntimeError(f'Failed to fetch clipboard entry id: {date}, {content_hash}')
        return int(row['id'])

    def list_by_date(
        self,
        date: str,
        filters: dict[str, Any] | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[sqlite3.Row]:
        where, params = self._where_by_date(date, filters)
        params.extend([int(limit), int(offset)])
        with self._lock:
            return list(
                self.conn.execute(
                    f"""
                    SELECT *
                    FROM clipboard_entries
                    WHERE {where}
                    ORDER BY last_seen_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    tuple(params),
                ).fetchall()
            )

    def count_by_date(self, date: str, filters: dict[str, Any] | None = None) -> int:
        where, params = self._where_by_date(date, filters)
        with self._lock:
            row = self.conn.execute(
                f"SELECT COUNT(*) AS n FROM clipboard_entries WHERE {where}",
                tuple(params),
            ).fetchone()
        return int(row['n'] if row else 0)

    def get_by_id(self, entry_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM clipboard_entries WHERE id = ?",
                (int(entry_id),),
            ).fetchone()

    def update_selected(self, entry_id: int, selected: bool) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE clipboard_entries
                SET is_selected = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(selected), _now(), int(entry_id)),
            )
            self.conn.commit()

    def mark_deleted(self, entry_id: int) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE clipboard_entries
                SET is_deleted = 1, updated_at = ?
                WHERE id = ?
                """,
                (_now(), int(entry_id)),
            )
            self.conn.commit()

    soft_delete = mark_deleted

    def update_annotation(
        self,
        source_type: str,
        source_id: int,
        category: str | None = None,
        note: str | None = None,
        importance: int | None = None,
    ) -> sqlite3.Row:
        from daily_report.storage.repositories.annotation_repository import AnnotationRepository

        return AnnotationRepository(self.conn).update_annotation(
            source_type=source_type,
            source_id=source_id,
            category=category,
            note=note,
            importance=importance,
        )

    def list_today_entries(self, date: str) -> list[sqlite3.Row]:
        return self.list_by_date(date, {'deleted': False}, limit=100000, offset=0)

    @staticmethod
    def _where_by_date(date: str, filters: dict[str, Any] | None) -> tuple[str, list[Any]]:
        filters = filters or {}
        clauses = ['date = ?']
        params: list[Any] = [date]

        if 'selected' in filters and filters['selected'] is not None:
            clauses.append('is_selected = ?')
            params.append(int(bool(filters['selected'])))
        if 'deleted' in filters and filters['deleted'] is not None:
            clauses.append('is_deleted = ?')
            params.append(int(bool(filters['deleted'])))
        if 'sensitive' in filters and filters['sensitive'] is not None:
            clauses.append('is_sensitive = ?')
            params.append(int(bool(filters['sensitive'])))
        if keyword := str(filters.get('keyword') or '').strip():
            like = f'%{keyword}%'
            clauses.append('(content_preview LIKE ? OR content LIKE ? OR sensitivity_reason LIKE ?)')
            params.extend([like, like, like])

        return ' AND '.join(clauses), params


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
