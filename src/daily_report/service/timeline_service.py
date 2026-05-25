from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Literal

from daily_report.service.category import (
    infer_category_for_ai_prompt,
    infer_category_for_app,
    infer_category_for_browser,
    infer_category_for_clipboard,
)
from daily_report.storage.database import create_connection, default_db_path, init_database
from daily_report.storage.repositories.annotation_repository import AnnotationRepository

SourceType = Literal['app', 'browser', 'clipboard', 'ai_prompt']


@dataclass(frozen=True)
class TimelineEvent:
    event_id: str
    source_type: SourceType
    source_id: int
    start_time: str
    end_time: str | None
    title: str
    subtitle: str
    content_preview: str
    category: str
    is_selected: bool
    is_sensitive: bool
    is_deleted: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TimelineService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()

    def list_timeline(
        self,
        date: str | None = None,
        source_types: list[str] | None = None,
        selected: bool | None = None,
        sensitive: bool | None = None,
        keyword: str | None = None,
        limit: int = 500,
        sort_order: str = 'asc',
    ) -> list[TimelineEvent]:
        day = date or date_cls.today().isoformat()
        wanted = self._normalize_source_types(source_types)
        events: list[TimelineEvent] = []
        with self._connect() as conn:
            annotations = AnnotationRepository(conn)
            if 'app' in wanted:
                events.extend(self._list_app(conn, annotations, day, selected, sensitive, keyword))
            if 'browser' in wanted:
                events.extend(self._list_browser(conn, annotations, day, selected, sensitive, keyword))
            if 'clipboard' in wanted:
                events.extend(self._list_clipboard(conn, annotations, day, selected, sensitive, keyword))
            if 'ai_prompt' in wanted:
                events.extend(self._list_ai_prompt(conn, annotations, day, selected, sensitive, keyword))

        reverse = sort_order.lower() == 'desc'
        events.sort(key=lambda event: (event.start_time or '', event.source_id), reverse=reverse)
        return events[: max(1, int(limit))]

    def update_entry_selection(self, source_type: str, source_id: int, selected: bool) -> None:
        table = self._source_table(source_type)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {table} SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(selected), int(source_id)),
            )
            conn.commit()

    def mark_entry_deleted(self, source_type: str, source_id: int) -> None:
        table = self._source_table(source_type)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {table} SET is_deleted = 1, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(source_id),),
            )
            conn.commit()

    def get_entry_detail(self, source_type: str, source_id: int) -> dict[str, Any] | None:
        table = self._source_table(source_type)
        with self._connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (int(source_id),)).fetchone()
            if row is None:
                return None
            data = dict(row)
            normalized = self._normalize_source_type(source_type)
            annotation = AnnotationRepository(conn).get_annotation(normalized, int(source_id))
            data['annotation'] = dict(annotation) if annotation else None
            return data

    def _list_app(
        self,
        conn: sqlite3.Connection,
        annotations: AnnotationRepository,
        day: str,
        selected: bool | None,
        sensitive: bool | None,
        keyword: str | None,
    ) -> list[TimelineEvent]:
        if sensitive is True or not _table_exists(conn, 'app_sessions'):
            return []
        clauses = ['a.date = ?']
        params: list[Any] = [day]
        if selected is not None:
            clauses.append('a.is_selected = ?')
            params.append(int(selected))
        clauses.append('a.is_deleted = 0')
        if keyword:
            like = f'%{keyword}%'
            clauses.append('(a.app_name LIKE ? OR a.window_title LIKE ? OR a.process_name LIKE ? OR p.display_name LIKE ?)')
            params.extend([like, like, like, like])
        rows = conn.execute(
            f"""
            SELECT
                a.*,
                p.display_name AS profile_display_name,
                p.category AS profile_category,
                p.color AS profile_color,
                p.track_enabled AS profile_track_enabled,
                p.capture_title_enabled AS profile_capture_title_enabled
            FROM app_sessions a
            LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
            WHERE {' AND '.join(clauses)}
            ORDER BY a.start_time ASC
            """,
            tuple(params),
        ).fetchall()
        annotation_map = annotations.get_annotations_for_ids('app', [int(row['id']) for row in rows])
        events = []
        for row in rows:
            annotation = annotation_map.get(int(row['id']), {})
            category = (
                annotation.get('category')
                or _row_optional_text(row, 'profile_category')
                or infer_category_for_app(row['process_name'], row['window_title'])
            )
            title = (
                _row_optional_text(row, 'profile_display_name')
                or str(row['app_name'] or row['process_name'] or '前台应用')
            )
            subtitle = str(row['window_title'] or '') if _row_bool(row, 'profile_capture_title_enabled', True) else ''
            events.append(
                TimelineEvent(
                    event_id=f"app:{row['id']}",
                    source_type='app',
                    source_id=int(row['id']),
                    start_time=str(row['start_time'] or ''),
                    end_time=str(row['end_time']) if row['end_time'] else None,
                    title=title,
                    subtitle=subtitle,
                    content_preview=subtitle,
                    category=category,
                    is_selected=bool(row['is_selected']),
                    is_sensitive=False,
                    is_deleted=bool(_row_get(row, 'is_deleted', 0)),
                )
            )
        return events

    def _list_browser(
        self,
        conn: sqlite3.Connection,
        annotations: AnnotationRepository,
        day: str,
        selected: bool | None,
        sensitive: bool | None,
        keyword: str | None,
    ) -> list[TimelineEvent]:
        if sensitive is True or not _table_exists(conn, 'browser_history_entries'):
            return []
        clauses = ['date = ?']
        params: list[Any] = [day]
        if selected is not None:
            clauses.append('is_selected = ?')
            params.append(int(selected))
        clauses.append('is_deleted = 0')
        if keyword:
            like = f'%{keyword}%'
            clauses.append('(title LIKE ? OR url LIKE ? OR domain LIKE ? OR search_query LIKE ?)')
            params.extend([like, like, like, like])
        rows = conn.execute(
            f"""
            SELECT *
            FROM browser_history_entries
            WHERE {' AND '.join(clauses)}
            ORDER BY visit_time ASC
            """,
            tuple(params),
        ).fetchall()
        annotation_map = annotations.get_annotations_for_ids('browser', [int(row['id']) for row in rows])
        events = []
        for row in rows:
            annotation = annotation_map.get(int(row['id']), {})
            category = annotation.get('category') or infer_category_for_browser(
                row['title'], row['url'], row['is_search'], row['search_query']
            )
            title = str(row['title'] or row['domain'] or '浏览记录')
            content_preview = str(row['search_query'] or row['url'] or '')
            events.append(
                TimelineEvent(
                    event_id=f"browser:{row['id']}",
                    source_type='browser',
                    source_id=int(row['id']),
                    start_time=str(row['visit_time'] or ''),
                    end_time=None,
                    title=title,
                    subtitle=str(row['domain'] or ''),
                    content_preview=content_preview,
                    category=category,
                    is_selected=bool(row['is_selected']),
                    is_sensitive=False,
                    is_deleted=bool(row['is_deleted']),
                )
            )
        return events

    def _list_clipboard(
        self,
        conn: sqlite3.Connection,
        annotations: AnnotationRepository,
        day: str,
        selected: bool | None,
        sensitive: bool | None,
        keyword: str | None,
    ) -> list[TimelineEvent]:
        if not _table_exists(conn, 'clipboard_entries'):
            return []
        clauses = ['date = ?']
        params: list[Any] = [day]
        if selected is not None:
            clauses.append('is_selected = ?')
            params.append(int(selected))
        if sensitive is not None:
            clauses.append('is_sensitive = ?')
            params.append(int(sensitive))
        clauses.append('is_deleted = 0')
        if keyword:
            like = f'%{keyword}%'
            clauses.append('(content_preview LIKE ? OR content LIKE ?)')
            params.extend([like, like])
        rows = conn.execute(
            f"""
            SELECT *
            FROM clipboard_entries
            WHERE {' AND '.join(clauses)}
            ORDER BY first_seen_at ASC
            """,
            tuple(params),
        ).fetchall()
        annotation_map = annotations.get_annotations_for_ids('clipboard', [int(row['id']) for row in rows])
        events = []
        for row in rows:
            annotation = annotation_map.get(int(row['id']), {})
            category = annotation.get('category') or infer_category_for_clipboard(row['content_preview'])
            events.append(
                TimelineEvent(
                    event_id=f"clipboard:{row['id']}",
                    source_type='clipboard',
                    source_id=int(row['id']),
                    start_time=str(row['first_seen_at'] or row['last_seen_at'] or ''),
                    end_time=str(row['last_seen_at']) if row['last_seen_at'] else None,
                    title='剪切板文本',
                    subtitle=f"{int(row['char_count'] or 0)} 字",
                    content_preview=str(row['content_preview'] or ''),
                    category=category,
                    is_selected=bool(row['is_selected']),
                    is_sensitive=bool(row['is_sensitive']),
                    is_deleted=bool(row['is_deleted']),
                )
            )
        return events

    def _list_ai_prompt(
        self,
        conn: sqlite3.Connection,
        annotations: AnnotationRepository,
        day: str,
        selected: bool | None,
        sensitive: bool | None,
        keyword: str | None,
    ) -> list[TimelineEvent]:
        if not _table_exists(conn, 'ai_prompt_entries'):
            return []
        clauses = ['date = ?']
        params: list[Any] = [day]
        if selected is not None:
            clauses.append('is_selected = ?')
            params.append(int(selected))
        if sensitive is not None:
            clauses.append('is_sensitive = ?')
            params.append(int(sensitive))
        clauses.append('is_deleted = 0')
        if keyword:
            like = f'%{keyword}%'
            clauses.append('(prompt_preview LIKE ? OR prompt_text LIKE ? OR page_title LIKE ? OR platform LIKE ?)')
            params.extend([like, like, like, like])
        rows = conn.execute(
            f"""
            SELECT *
            FROM ai_prompt_entries
            WHERE {' AND '.join(clauses)}
            ORDER BY timestamp ASC
            """,
            tuple(params),
        ).fetchall()
        annotation_map = annotations.get_annotations_for_ids('ai_prompt', [int(row['id']) for row in rows])
        events = []
        for row in rows:
            annotation = annotation_map.get(int(row['id']), {})
            category = annotation.get('category') or infer_category_for_ai_prompt(row['prompt_preview'])
            platform = str(row['platform'] or 'AI')
            events.append(
                TimelineEvent(
                    event_id=f"ai_prompt:{row['id']}",
                    source_type='ai_prompt',
                    source_id=int(row['id']),
                    start_time=str(row['timestamp'] or ''),
                    end_time=None,
                    title=f'{platform} 提问',
                    subtitle=str(row['page_title'] or ''),
                    content_preview=str(row['prompt_preview'] or ''),
                    category=category,
                    is_selected=bool(row['is_selected']),
                    is_sensitive=bool(row['is_sensitive']),
                    is_deleted=bool(row['is_deleted']),
                )
            )
        return events

    def _connect(self) -> sqlite3.Connection:
        conn = create_connection(self.db_path)
        init_database(conn)
        return conn

    @classmethod
    def _normalize_source_types(cls, source_types: list[str] | None) -> set[str]:
        if not source_types:
            return {'app', 'browser', 'clipboard', 'ai_prompt'}
        return {cls._normalize_source_type(source_type) for source_type in source_types}

    @staticmethod
    def _normalize_source_type(source_type: str) -> SourceType:
        normalized = str(source_type or '').strip()
        if normalized == 'ai':
            normalized = 'ai_prompt'
        if normalized not in {'app', 'browser', 'clipboard', 'ai_prompt'}:
            raise ValueError(f'Unsupported source_type: {source_type}')
        return normalized  # type: ignore[return-value]

    @classmethod
    def _source_table(cls, source_type: str) -> str:
        mapping = {
            'app': 'app_sessions',
            'browser': 'browser_history_entries',
            'clipboard': 'clipboard_entries',
            'ai_prompt': 'ai_prompt_entries',
        }
        return mapping[cls._normalize_source_type(source_type)]


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _row_get(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    return row[key] if key in row.keys() else default


def _row_optional_text(row: sqlite3.Row, key: str) -> str | None:
    value = str(_row_get(row, key, '') or '').strip()
    return value or None


def _row_bool(row: sqlite3.Row, key: str, default: bool) -> bool:
    value = _row_get(row, key, int(default))
    if value is None:
        value = int(default)
    return bool(value)
