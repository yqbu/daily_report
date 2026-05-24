from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Any


class AiPromptEntryRepository:
    """Repository for prompts submitted by the user on AI chat pages."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def upsert_prompt(self, entry: dict[str, Any] | Any) -> tuple[int, bool]:
        values = _entry_values(entry)
        if values['is_sensitive']:
            values['is_selected'] = False

        now = _now()
        with self._lock:
            existing = self.conn.execute(
                """
                SELECT id
                FROM ai_prompt_entries
                WHERE date = ? AND platform = ? AND prompt_hash = ?
                """,
                (values['date'], values['platform'], values['prompt_hash']),
            ).fetchone()

            if existing is not None:
                self.conn.execute(
                    """
                    UPDATE ai_prompt_entries
                    SET timestamp = ?,
                        conversation_url = ?,
                        page_title = ?,
                        prompt_text = ?,
                        prompt_preview = ?,
                        char_count = ?,
                        is_sensitive = ?,
                        sensitivity_reason = ?,
                        client_event_id = ?,
                        source = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        _timestamp_text(values['timestamp']),
                        values['conversation_url'],
                        values['page_title'],
                        values['prompt_text'],
                        values['prompt_preview'],
                        int(values['char_count']),
                        int(values['is_sensitive']),
                        values['sensitivity_reason'],
                        values['client_event_id'],
                        values['source'],
                        now,
                        int(existing['id']),
                    ),
                )
                self.conn.commit()
                return int(existing['id']), True

            cursor = self.conn.execute(
                """
                INSERT INTO ai_prompt_entries (
                    date, timestamp, platform, conversation_url, page_title, prompt_text,
                    prompt_preview, prompt_hash, dedupe_key, char_count, is_sensitive,
                    sensitivity_reason, is_selected, is_deleted, client_event_id, source,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """,
                (
                    values['date'],
                    _timestamp_text(values['timestamp']),
                    values['platform'],
                    values['conversation_url'],
                    values['page_title'],
                    values['prompt_text'],
                    values['prompt_preview'],
                    values['prompt_hash'],
                    values['dedupe_key'],
                    int(values['char_count']),
                    int(values['is_sensitive']),
                    values['sensitivity_reason'],
                    int(values['is_selected']),
                    values['client_event_id'],
                    values['source'],
                    now,
                    now,
                ),
            )
            self.conn.commit()
            return int(cursor.lastrowid), False

    def upsert_entry(
        self,
        *,
        date: str,
        timestamp: datetime,
        platform: str,
        conversation_url: str,
        page_title: str,
        prompt_text: str,
        prompt_preview: str,
        prompt_hash: str,
        dedupe_key: str | None = None,
        char_count: int,
        is_sensitive: bool,
        sensitivity_reason: str | None,
        is_selected: bool,
        client_event_id: str | None = None,
        source: str = 'edge_extension',
    ) -> tuple[int, bool]:
        return self.upsert_prompt(
            {
                'date': date,
                'timestamp': timestamp,
                'platform': platform,
                'conversation_url': conversation_url,
                'page_title': page_title,
                'prompt_text': prompt_text,
                'prompt_preview': prompt_preview,
                'prompt_hash': prompt_hash,
                'dedupe_key': dedupe_key,
                'char_count': char_count,
                'is_sensitive': is_sensitive,
                'sensitivity_reason': sensitivity_reason,
                'is_selected': is_selected,
                'client_event_id': client_event_id,
                'source': source,
            }
        )

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
                    FROM ai_prompt_entries
                    WHERE {where}
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    tuple(params),
                ).fetchall()
            )

    def count_by_date(self, date: str, filters: dict[str, Any] | None = None) -> int:
        where, params = self._where_by_date(date, filters)
        with self._lock:
            row = self.conn.execute(
                f"SELECT COUNT(*) AS n FROM ai_prompt_entries WHERE {where}",
                tuple(params),
            ).fetchone()
        return int(row['n'] if row else 0)

    def get_by_id(self, entry_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM ai_prompt_entries WHERE id = ?",
                (int(entry_id),),
            ).fetchone()

    def update_selected(self, entry_id: int, selected: bool) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE ai_prompt_entries
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
                UPDATE ai_prompt_entries
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
        if platform := str(filters.get('platform') or '').strip():
            clauses.append('platform = ?')
            params.append(platform)
        if keyword := str(filters.get('keyword') or '').strip():
            like = f'%{keyword}%'
            clauses.append(
                '(platform LIKE ? OR page_title LIKE ? OR prompt_preview LIKE ? '
                'OR prompt_text LIKE ? OR conversation_url LIKE ?)'
            )
            params.extend([like, like, like, like, like])

        return ' AND '.join(clauses), params


def _entry_values(entry: dict[str, Any] | Any) -> dict[str, Any]:
    def get(name: str, default: Any = None) -> Any:
        if isinstance(entry, dict):
            return entry.get(name, default)
        return getattr(entry, name, default)

    return {
        'date': str(get('date') or '').strip(),
        'timestamp': get('timestamp'),
        'platform': str(get('platform') or 'Unknown').strip()[:64],
        'conversation_url': str(get('conversation_url') or '').strip()[:2048],
        'page_title': str(get('page_title') or '').strip()[:512],
        'prompt_text': str(get('prompt_text') or ''),
        'prompt_preview': str(get('prompt_preview') or ''),
        'prompt_hash': str(get('prompt_hash') or ''),
        'dedupe_key': str(get('dedupe_key') or '').strip() or None,
        'char_count': int(get('char_count') or 0),
        'is_sensitive': bool(get('is_sensitive') or False),
        'sensitivity_reason': get('sensitivity_reason'),
        'is_selected': bool(get('is_selected') if get('is_selected') is not None else True),
        'client_event_id': str(get('client_event_id') or '').strip()[:128] or None,
        'source': str(get('source') or 'edge_extension').strip()[:64],
    }


def _timestamp_text(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec='seconds')
    return str(value or _now())


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
