from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import asdict
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.service.category import (
    infer_category_for_ai_prompt,
    infer_category_for_app,
    infer_category_for_browser,
    infer_category_for_clipboard,
)
from daily_report.service.sensitivity import make_preview
from daily_report.storage.database import create_connection, default_db_path, init_database
from daily_report.storage.repositories.annotation_repository import AnnotationRepository


class MaterialService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()

    def build_materials(
        self,
        date: str | None = None,
        include_sensitive: bool = False,
    ) -> list[MaterialCard]:
        day = date or date_cls.today().isoformat()
        with self._connect() as conn:
            materials: list[MaterialCard] = []
            materials.extend(self._build_app_materials(conn, day))
            materials.extend(self._build_browser_materials(conn, day))
            materials.extend(self._build_clipboard_materials(conn, day, include_sensitive))
            materials.extend(self._build_ai_prompt_materials(conn, day, include_sensitive))
        materials.sort(key=lambda item: (item.category, item.time_range, item.source_type))
        return materials

    def build_snapshot(
        self,
        date: str | None = None,
        include_sensitive: bool = False,
    ) -> dict[str, Any]:
        day = date or date_cls.today().isoformat()
        materials = self.build_materials(day, include_sensitive=include_sensitive)
        return {
            'date': day,
            'materials': [asdict(material) for material in materials],
            'source_counts': self.count_selected_sources(day, include_sensitive=include_sensitive),
        }

    def count_selected_sources(
        self,
        date: str | None = None,
        include_sensitive: bool = False,
    ) -> dict[str, int]:
        day = date or date_cls.today().isoformat()
        with self._connect() as conn:
            return {
                'app': _count(
                    conn,
                    "SELECT COUNT(*) AS n FROM app_sessions WHERE date = ? AND is_selected = 1 AND is_deleted = 0",
                    (day,),
                ),
                'browser': _count(
                    conn,
                    """
                    SELECT COUNT(*) AS n
                    FROM browser_history_entries
                    WHERE date = ? AND is_selected = 1 AND is_deleted = 0 AND is_noise = 0
                    """,
                    (day,),
                ),
                'clipboard': _count(
                    conn,
                    """
                    SELECT COUNT(*) AS n
                    FROM clipboard_entries
                    WHERE date = ? AND is_selected = 1 AND is_deleted = 0
                      AND (? = 1 OR is_sensitive = 0)
                    """,
                    (day, int(include_sensitive)),
                ),
                'ai_prompt': _count(
                    conn,
                    """
                    SELECT COUNT(*) AS n
                    FROM ai_prompt_entries
                    WHERE date = ? AND is_selected = 1 AND is_deleted = 0
                      AND (? = 1 OR is_sensitive = 0)
                    """,
                    (day, int(include_sensitive)),
                ),
            }

    def _build_app_materials(self, conn: sqlite3.Connection, day: str) -> list[MaterialCard]:
        if not _table_exists(conn, 'app_sessions'):
            return []
        rows = conn.execute(
            """
            SELECT *
            FROM app_sessions
            WHERE date = ? AND is_selected = 1 AND is_deleted = 0
              AND COALESCE(active_duration_sec, duration_sec, 0) >= 10
            ORDER BY start_time ASC
            """,
            (day,),
        ).fetchall()
        annotations = AnnotationRepository(conn).get_annotations_for_ids('app', [int(row['id']) for row in rows])
        grouped: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
        for row in rows:
            grouped[(str(row['app_name'] or ''), str(row['window_title'] or ''))].append(row)

        materials: list[MaterialCard] = []
        for group_rows in grouped.values():
            first = group_rows[0]
            source_ids = [int(row['id']) for row in group_rows]
            active_sec = sum(float(row['active_duration_sec'] or row['duration_sec'] or 0) for row in group_rows)
            annotation = annotations.get(source_ids[0], {})
            category = annotation.get('category') or infer_category_for_app(
                first['process_name'],
                first['window_title'],
            )
            title = str(first['app_name'] or first['process_name'] or '前台应用')
            evidence = str(first['window_title'] or title)
            materials.append(
                MaterialCard(
                    source_type='app',
                    source_id=source_ids[0],
                    time_range=f"{_hhmm(first['start_time'])}-{_hhmm(group_rows[-1]['end_time'])}",
                    category=category,
                    title=title,
                    summary=f"{title} 使用约 {_format_seconds(active_sec)}，相关窗口 {len(group_rows)} 次。",
                    evidence=evidence,
                    importance=int(annotation.get('importance') or 0),
                    is_sensitive=False,
                )
            )
        return materials

    def _build_browser_materials(self, conn: sqlite3.Connection, day: str) -> list[MaterialCard]:
        if not _table_exists(conn, 'browser_history_entries'):
            return []
        rows = conn.execute(
            """
            SELECT *
            FROM browser_history_entries
            WHERE date = ? AND is_selected = 1 AND is_deleted = 0 AND is_noise = 0
            ORDER BY is_search DESC, visit_time ASC
            LIMIT 120
            """,
            (day,),
        ).fetchall()
        annotations = AnnotationRepository(conn).get_annotations_for_ids(
            'browser', [int(row['id']) for row in rows]
        )
        materials = []
        for row in rows:
            annotation = annotations.get(int(row['id']), {})
            category = annotation.get('category') or infer_category_for_browser(
                row['title'], row['url'], row['is_search'], row['search_query']
            )
            if row['is_search']:
                title = f"搜索：{row['search_query'] or row['title'] or row['domain']}"
                summary = f"通过 {row['search_engine'] or '搜索引擎'} 调研：{row['search_query'] or ''}"
                evidence = str(row['search_query'] or row['url'] or '')
            else:
                title = str(row['title'] or row['domain'] or '浏览记录')
                summary = f"浏览 {row['domain'] or '网页'}：{title}"
                evidence = str(row['url'] or title)
            materials.append(
                MaterialCard(
                    source_type='browser',
                    source_id=int(row['id']),
                    time_range=_hhmm(row['visit_time']),
                    category=category,
                    title=make_preview(title, 120),
                    summary=make_preview(summary, 180),
                    evidence=make_preview(evidence, 220),
                    importance=int(annotation.get('importance') or 0),
                    is_sensitive=False,
                )
            )
        return materials

    def _build_clipboard_materials(
        self,
        conn: sqlite3.Connection,
        day: str,
        include_sensitive: bool,
    ) -> list[MaterialCard]:
        if not _table_exists(conn, 'clipboard_entries'):
            return []
        rows = conn.execute(
            """
            SELECT *
            FROM clipboard_entries
            WHERE date = ? AND is_selected = 1 AND is_deleted = 0
              AND (? = 1 OR is_sensitive = 0)
            ORDER BY last_seen_at ASC
            LIMIT 100
            """,
            (day, int(include_sensitive)),
        ).fetchall()
        annotations = AnnotationRepository(conn).get_annotations_for_ids(
            'clipboard', [int(row['id']) for row in rows]
        )
        materials = []
        for row in rows:
            annotation = annotations.get(int(row['id']), {})
            preview = str(row['content_preview'] or '')
            category = annotation.get('category') or infer_category_for_clipboard(preview)
            materials.append(
                MaterialCard(
                    source_type='clipboard',
                    source_id=int(row['id']),
                    time_range=_hhmm(row['last_seen_at']),
                    category=category,
                    title='剪切板文本',
                    summary=f"剪切板记录，约 {int(row['char_count'] or len(preview))} 字。",
                    evidence=make_preview(preview, 220),
                    importance=int(annotation.get('importance') or 0),
                    is_sensitive=bool(row['is_sensitive']),
                )
            )
        return materials

    def _build_ai_prompt_materials(
        self,
        conn: sqlite3.Connection,
        day: str,
        include_sensitive: bool,
    ) -> list[MaterialCard]:
        if not _table_exists(conn, 'ai_prompt_entries'):
            return []
        rows = conn.execute(
            """
            SELECT *
            FROM ai_prompt_entries
            WHERE date = ? AND is_selected = 1 AND is_deleted = 0
              AND (? = 1 OR is_sensitive = 0)
            ORDER BY timestamp ASC
            LIMIT 100
            """,
            (day, int(include_sensitive)),
        ).fetchall()
        annotations = AnnotationRepository(conn).get_annotations_for_ids(
            'ai_prompt', [int(row['id']) for row in rows]
        )
        materials = []
        for row in rows:
            annotation = annotations.get(int(row['id']), {})
            preview = str(row['prompt_preview'] or '')
            category = annotation.get('category') or infer_category_for_ai_prompt(preview)
            platform = str(row['platform'] or 'AI')
            materials.append(
                MaterialCard(
                    source_type='ai_prompt',
                    source_id=int(row['id']),
                    time_range=_hhmm(row['timestamp']),
                    category=category,
                    title=f'{platform} 提问',
                    summary=f"向 {platform} 提问：{make_preview(preview, 160)}",
                    evidence=make_preview(preview, 240),
                    importance=int(annotation.get('importance') or 0),
                    is_sensitive=bool(row['is_sensitive']),
                )
            )
        return materials

    def _connect(self) -> sqlite3.Connection:
        conn = create_connection(self.db_path)
        init_database(conn)
        return conn


def _count(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
    except sqlite3.Error:
        return 0
    return int(row['n'] if row else 0)


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


def _hhmm(value: Any) -> str:
    text = str(value or '')
    if len(text) >= 16 and text[10] in {' ', 'T'}:
        return text[11:16]
    return text[:5]


def _format_seconds(value: float) -> str:
    seconds = int(value or 0)
    hours, rem = divmod(seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f'{hours}h{minutes:02d}m'
    if minutes:
        return f'{minutes}m'
    return f'{seconds}s'
