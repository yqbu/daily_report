from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

SOURCE_TYPES = {'app', 'browser', 'clipboard'}


class EntryAnnotationV2Repository:
    """Entry-key based annotation repository for unified source records."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_by_entry_key(self, entry_key: str) -> sqlite3.Row | None:
        entry_key = _validate_entry_key(entry_key)
        return self.conn.execute(
            """
            SELECT *
            FROM entry_annotations_v2
            WHERE entry_key = ?
            """,
            (entry_key,),
        ).fetchone()

    def upsert_annotation(
        self,
        entry_key: str,
        source_type: str,
        record_type: str | None = None,
        category: str | None = None,
        note: str | None = None,
        importance: int | None = None,
        is_selected_override: bool | None = None,
        is_sensitive_override: bool | None = None,
        sensitivity_reason_override: str | None = None,
    ) -> sqlite3.Row:
        entry_key = _validate_entry_key(entry_key)
        source_type = _validate_source_type(source_type)
        existing = self.get_by_entry_key(entry_key)
        importance_value = (
            _clamp_importance(importance)
            if importance is not None
            else int(existing['importance']) if existing is not None else 0
        )
        now = _now()

        self.conn.execute(
            """
            INSERT INTO entry_annotations_v2 (
                entry_key,
                source_type,
                record_type,
                category,
                note,
                importance,
                is_selected_override,
                is_sensitive_override,
                sensitivity_reason_override,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entry_key)
            DO UPDATE SET
                source_type = excluded.source_type,
                record_type = COALESCE(excluded.record_type, entry_annotations_v2.record_type),
                category = COALESCE(excluded.category, entry_annotations_v2.category),
                note = COALESCE(excluded.note, entry_annotations_v2.note),
                importance = excluded.importance,
                is_selected_override = COALESCE(excluded.is_selected_override, entry_annotations_v2.is_selected_override),
                is_sensitive_override = COALESCE(excluded.is_sensitive_override, entry_annotations_v2.is_sensitive_override),
                sensitivity_reason_override = COALESCE(excluded.sensitivity_reason_override, entry_annotations_v2.sensitivity_reason_override),
                updated_at = excluded.updated_at
            """,
            (
                entry_key,
                source_type,
                _clean_text(record_type),
                _clean_text(category),
                _clean_text(note),
                importance_value,
                _optional_bool_int(is_selected_override),
                _optional_bool_int(is_sensitive_override),
                _clean_text(sensitivity_reason_override),
                now,
                now,
            ),
        )
        self.conn.commit()
        row = self.get_by_entry_key(entry_key)
        if row is None:
            raise RuntimeError(f'Failed to upsert annotation for {entry_key}')
        return row

    def batch_get_by_entry_keys(self, entry_keys: list[str]) -> dict[str, dict[str, Any]]:
        keys = [_validate_entry_key(key) for key in entry_keys if str(key or '').strip()]
        if not keys:
            return {}
        placeholders = ','.join('?' for _ in keys)
        rows = self.conn.execute(
            f"""
            SELECT *
            FROM entry_annotations_v2
            WHERE entry_key IN ({placeholders})
            """,
            tuple(keys),
        ).fetchall()
        return {str(row['entry_key']): dict(row) for row in rows}

    def update_importance(self, entry_key: str, importance: int) -> sqlite3.Row:
        row = self.get_by_entry_key(entry_key)
        return self.upsert_annotation(
            entry_key=entry_key,
            source_type=str(row['source_type']) if row else _source_type_from_entry_key(entry_key),
            record_type=str(row['record_type']) if row and row['record_type'] else _record_type_from_entry_key(entry_key),
            importance=_clamp_importance(importance),
        )

    def update_category(self, entry_key: str, category: str | None) -> sqlite3.Row:
        return self._update_field(entry_key, category=category)

    def update_note(self, entry_key: str, note: str | None) -> sqlite3.Row:
        return self._update_field(entry_key, note=note)

    def update_sensitive_override(
        self,
        entry_key: str,
        sensitive: bool | None,
        reason: str | None,
    ) -> sqlite3.Row:
        return self._update_field(
            entry_key,
            is_sensitive_override=sensitive,
            sensitivity_reason_override=reason,
        )

    def update_selected_override(self, entry_key: str, selected: bool | None) -> sqlite3.Row:
        return self._update_field(entry_key, is_selected_override=selected)

    def _update_field(self, entry_key: str, **payload: Any) -> sqlite3.Row:
        row = self.get_by_entry_key(entry_key)
        if row is None:
            return self.upsert_annotation(
                entry_key=entry_key,
                source_type=_source_type_from_entry_key(entry_key),
                record_type=_record_type_from_entry_key(entry_key),
                **payload,
            )
        assignments = []
        params: list[Any] = []
        for key, value in payload.items():
            assignments.append(f'{key} = ?')
            if key == 'importance':
                params.append(_clamp_importance(value))
            elif key in {'is_selected_override', 'is_sensitive_override'}:
                params.append(_optional_bool_int(value))
            else:
                params.append(_clean_text(value))
        if assignments:
            params.extend([_now(), _validate_entry_key(entry_key)])
            self.conn.execute(
                f"""
                UPDATE entry_annotations_v2
                SET {', '.join(assignments)}, updated_at = ?
                WHERE entry_key = ?
                """,
                tuple(params),
            )
            self.conn.commit()
        updated = self.get_by_entry_key(entry_key)
        if updated is None:
            raise RuntimeError(f'Failed to update annotation for {entry_key}')
        return updated


def _validate_entry_key(entry_key: str) -> str:
    text = str(entry_key or '').strip()
    if not text:
        raise ValueError('entry_key is required')
    return text


def _validate_source_type(source_type: str) -> str:
    text = str(source_type or '').strip()
    if text not in SOURCE_TYPES:
        raise ValueError(f'Unsupported annotation source_type: {source_type}')
    return text


def _source_type_from_entry_key(entry_key: str) -> str:
    prefix = _validate_entry_key(entry_key).split(':', 1)[0]
    return _validate_source_type(prefix)


def _record_type_from_entry_key(entry_key: str) -> str | None:
    parts = _validate_entry_key(entry_key).split(':')
    if len(parts) < 2:
        return None
    if parts[0] == 'browser':
        return {'history': 'history_visit', 'ai_prompt': 'ai_prompt', 'event': None}.get(parts[1], parts[1])
    return None


def _clamp_importance(value: int | None) -> int:
    try:
        number = int(value if value is not None else 0)
    except (TypeError, ValueError):
        number = 0
    return max(0, min(100, number))


def _optional_bool_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return int(bool(value))


def _clean_text(value: str | None) -> str | None:
    text = str(value or '').strip()
    return text or None


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
