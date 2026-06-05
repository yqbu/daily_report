from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from daily_report.service.sensitivity import make_preview


class BrowserEventRepository:
    """Repository for lightweight browser behavior events from the extension."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def insert_event(self, event: dict[str, Any]) -> int:
        values = _event_values(event)
        now = _now()
        with self._lock:
            cursor = self.conn.execute(
                """
                INSERT INTO browser_events (
                    date, timestamp, record_type, event_type, url, title, domain, tab_id, window_id,
                    duration_sec, content_preview, search_engine, search_query, referrer,
                    payload_json, client_event_id, source, importance, is_sensitive, sensitivity_reason,
                    is_selected, is_deleted, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    values['date'],
                    values['timestamp'],
                    values['record_type'],
                    values['event_type'],
                    values['url'],
                    values['title'],
                    values['domain'],
                    values['tab_id'],
                    values['window_id'],
                    float(values['duration_sec']),
                    values['content_preview'],
                    values['search_engine'],
                    values['search_query'],
                    values['referrer'],
                    values['payload_json'],
                    values['client_event_id'],
                    values['source'],
                    int(values['importance']),
                    int(values['is_sensitive']),
                    values['sensitivity_reason'],
                    int(values['is_selected']),
                    now,
                    now,
                ),
            )
            self.conn.commit()
            return int(cursor.lastrowid)

    def upsert_event(self, event: dict[str, Any]) -> tuple[int, bool]:
        values = _event_values(event)
        client_event_id = values['client_event_id']
        with self._lock:
            if client_event_id:
                existing = self.conn.execute(
                    "SELECT id FROM browser_events WHERE client_event_id = ?",
                    (client_event_id,),
                ).fetchone()
                if existing is not None:
                    return int(existing['id']), True
            return self.insert_event(values), False

    def list_by_date(
        self,
        date: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[sqlite3.Row]:
        where, params = self._where_by_date(date, filters)
        params.extend([int(limit), int(offset)])
        with self._lock:
            return list(
                self.conn.execute(
                    f"""
                    SELECT *
                    FROM browser_events
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
                f"SELECT COUNT(*) AS n FROM browser_events WHERE {where}",
                tuple(params),
            ).fetchone()
        return int(row['n'] if row else 0)

    def get_by_id(self, event_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM browser_events WHERE id = ?",
                (int(event_id),),
            ).fetchone()

    def update_selected(self, event_id: int, selected: bool) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE browser_events
                SET is_selected = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(selected), _now(), int(event_id)),
            )
            self.conn.commit()

    def update_deleted(self, event_id: int, deleted: bool) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE browser_events
                SET is_deleted = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(deleted), _now(), int(event_id)),
            )
            self.conn.commit()

    def mark_deleted(self, event_id: int) -> None:
        self.update_deleted(event_id, True)

    def count_today_by_type(self, date: str) -> dict[str, int]:
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT record_type, COUNT(*) AS n
                FROM browser_events
                WHERE date = ? AND is_deleted = 0
                GROUP BY record_type
                """,
                (date,),
            ).fetchall()
        return {str(row['record_type']): int(row['n'] or 0) for row in rows}

    def count_by_domain(self, date: str, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT COALESCE(NULLIF(domain, ''), 'unknown') AS domain, COUNT(*) AS count
                FROM browser_events
                WHERE date = ? AND is_deleted = 0
                GROUP BY COALESCE(NULLIF(domain, ''), 'unknown')
                ORDER BY count DESC
                LIMIT ?
                """,
                (date, int(limit)),
            ).fetchall()
        return [{'domain': str(row['domain']), 'count': int(row['count'] or 0)} for row in rows]

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
        if record_type := str(filters.get('record_type') or filters.get('event_type') or '').strip():
            clauses.append('record_type = ?')
            params.append(_record_type(record_type, record_type))
        if domain := str(filters.get('domain') or '').strip():
            clauses.append('domain = ?')
            params.append(domain)
        if keyword := str(filters.get('keyword') or '').strip():
            like = f'%{keyword}%'
            clauses.append(
                '(url LIKE ? OR title LIKE ? OR domain LIKE ? OR search_query LIKE ? OR content_preview LIKE ?)'
            )
            params.extend([like, like, like, like, like])

        return ' AND '.join(clauses), params


def _event_values(event: dict[str, Any]) -> dict[str, Any]:
    timestamp = _timestamp_text(event.get('timestamp'))
    url = _trim(event.get('url'), 2000)
    domain = _trim(event.get('domain'), 255) or _extract_domain(url)
    payload = event.get('payload_json')
    if payload is None:
        payload = _payload_json(event.get('payload'))
    return {
        'date': str(event.get('date') or timestamp[:10]),
        'timestamp': timestamp,
        'record_type': _record_type(event.get('record_type'), event.get('event_type')),
        'event_type': _trim(event.get('event_type') or event.get('record_type'), 64) or 'page_view',
        'url': url,
        'title': _trim(event.get('title'), 300),
        'domain': domain,
        'tab_id': _trim(event.get('tab_id'), 128),
        'window_id': _trim(event.get('window_id'), 128),
        'duration_sec': float(event.get('duration_sec') or 0),
        'content_preview': make_preview(str(event.get('content_preview') or ''), 300) or None,
        'search_engine': _trim(event.get('search_engine'), 64),
        'search_query': make_preview(str(event.get('search_query') or ''), 200) or None,
        'referrer': _trim(event.get('referrer'), 2000),
        'payload_json': payload,
        'client_event_id': _trim(event.get('client_event_id'), 160),
        'source': _trim(event.get('source'), 64) or 'edge_extension',
        'importance': _clamp_int(event.get('importance'), 0, 100, 0),
        'is_sensitive': bool(event.get('is_sensitive') or False),
        'sensitivity_reason': _trim(event.get('sensitivity_reason'), 255),
        'is_selected': bool(event.get('is_selected') or False),
    }


def _timestamp_text(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec='seconds')
    text = str(value or '').strip()
    if not text:
        return _now()
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return _now()
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.isoformat(timespec='seconds')


def _payload_json(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    safe_payload = {}
    for key, item in value.items():
        text_key = str(key)[:80]
        if isinstance(item, (str, int, float, bool)) or item is None:
            safe_payload[text_key] = make_preview(str(item), 500) if isinstance(item, str) else item
    return json.dumps(safe_payload, ensure_ascii=False)


def _extract_domain(url: str | None) -> str | None:
    try:
        host = urlparse(str(url or '')).hostname
    except Exception:
        host = None
    return host.lower()[:255] if host else None


def _trim(value: Any, max_len: int) -> str | None:
    text = str(value or '').replace('\x00', '').strip()
    return text[:max_len] if text else None


def _record_type(record_type: Any, event_type: Any) -> str:
    normalized = str(record_type or '').strip()
    if normalized:
        return normalized[:64]
    raw_event_type = str(event_type or '').strip()
    if raw_event_type == 'ai_prompt_submit':
        return 'ai_prompt'
    return (raw_event_type or 'page_view')[:64]


def _clamp_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    return max(minimum, min(maximum, number))


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
