from __future__ import annotations

from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.service.category import infer_category_for_app
from daily_report.sources.base import (
    RawEvent,
    SourceAdapter,
    TimelineEvent,
    format_seconds,
    hhmm,
    limit_clause,
    optional_text,
    row_bool,
    row_get,
    table_exists,
    with_limit,
)
from daily_report.storage.repositories.annotation_repository import AnnotationRepository


class AppSourceAdapter(SourceAdapter):
    source_type = 'app'

    def list_raw_by_date(
        self,
        date: str,
        selected: bool | None = None,
        sensitive: bool | None = None,
        keyword: str | None = None,
        include_deleted: bool = False,
        limit: int | None = 500,
        offset: int = 0,
    ) -> list[RawEvent]:
        with self._connect() as conn:
            if not table_exists(conn, 'app_sessions'):
                return []
            clauses = ['a.date = ?']
            params: list[Any] = [date]
            if selected is not None:
                clauses.append('a.is_selected = ?')
                params.append(int(selected))
            if not include_deleted:
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
                ORDER BY a.start_time ASC, a.id ASC
                {limit_clause(limit)}
                """,
                tuple(with_limit(params, limit, offset)),
            ).fetchall()
            annotation_map = AnnotationRepository(conn).get_annotations_for_ids('app', [int(row['id']) for row in rows])
        raw_events = []
        for row in rows:
            data = dict(row)
            data['annotation'] = annotation_map.get(int(row['id']), {})
            if sensitive is not None and bool(data['annotation'].get('is_sensitive_override') or 0) is not sensitive:
                continue
            raw_events.append(RawEvent(self.source_type, int(row['id']), data))
        return raw_events

    def get_raw_detail(self, source_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM app_sessions WHERE id = ?', (int(source_id),)).fetchone()
            if row is None:
                return None
            data = dict(row)
            annotation = AnnotationRepository(conn).get_annotation('app', int(source_id))
            data['annotation'] = dict(annotation) if annotation else None
            return data

    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        row = raw_event.raw
        annotation = row.get('annotation') or {}
        category = (
            annotation.get('category')
            or optional_text(row, 'profile_category')
            or infer_category_for_app(str(row.get('process_name') or ''), str(row.get('window_title') or ''))
        )
        title = optional_text(row, 'profile_display_name') or str(row.get('app_name') or row.get('process_name') or '前台应用')
        subtitle = str(row.get('window_title') or '') if row_bool(row, 'profile_capture_title_enabled', True) else ''
        return TimelineEvent(
            event_id=f"app:{raw_event.source_id}",
            source_type='app',
            source_id=raw_event.source_id,
            start_time=str(row.get('start_time') or ''),
            end_time=str(row.get('end_time')) if row.get('end_time') else None,
            title=title,
            subtitle=subtitle,
            content_preview=subtitle,
            category=category,
            is_selected=bool(row.get('is_selected')),
            is_sensitive=bool(annotation.get('is_sensitive_override') or 0),
            is_deleted=bool(row_get(row, 'is_deleted', 0)),
            raw=row,
        )

    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        rows = _material_rows(event)
        if not rows:
            return None
        if not row_bool(rows[0], 'profile_track_enabled', True):
            return None
        active_sec = sum(float(row.get('active_duration_sec') or row.get('duration_sec') or 0) for row in rows)
        if active_sec < 10:
            return None
        annotation = rows[0].get('annotation') or {}
        window_titles = _unique_non_empty(str(row.get('window_title') or '') for row in rows if row_bool(row, 'profile_capture_title_enabled', True))
        if window_titles:
            evidence_parts = [f"时间段：{_format_time_ranges(rows)}", '窗口线索：' + '；'.join(window_titles[:8])]
            evidence = '；'.join(evidence_parts)
        else:
            evidence = event.title
        return MaterialCard(
            source_type='app',
            source_id=event.source_id,
            time_range=f"{hhmm(event.start_time)}-{hhmm(event.end_time or event.start_time)}",
            category=event.category,
            title=event.title,
            summary=f"{event.title} 使用约 {format_seconds(active_sec)}，包含 {len(rows)} 个前台应用时间段。",
            evidence=evidence,
            importance=int(annotation.get('importance') or 0),
            is_sensitive=False,
        )

    def update_selected(self, source_id: int, selected: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE app_sessions SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(selected), int(source_id)),
            )
            conn.commit()

    def update_deleted(self, source_id: int, deleted: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE app_sessions SET is_deleted = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(deleted), int(source_id)),
            )
            conn.commit()


def _material_rows(event: TimelineEvent) -> list[dict[str, Any]]:
    if event.raw and isinstance(event.raw.get('items'), list):
        return [item for item in event.raw['items'] if isinstance(item, dict)]
    if event.raw:
        return [event.raw]
    return []


def _unique_non_empty(values) -> list[str]:
    items: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if text and text not in items:
            items.append(text)
    return items


def _format_time_ranges(rows: list[dict[str, Any]]) -> str:
    ranges: list[str] = []
    for row in rows[:8]:
        start = hhmm(row.get('start_time'))
        end = hhmm(row.get('end_time'))
        text = f'{start}-{end}' if start and end else start or end
        if text and text not in ranges:
            ranges.append(text)
    if len(rows) > 8:
        ranges.append('等')
    return '、'.join(ranges) if ranges else '-'
