from __future__ import annotations

from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.service.category import infer_category_for_browser
from daily_report.service.sensitivity import make_preview
from daily_report.sources.base import RawEvent, SourceAdapter, TimelineEvent, hhmm, limit_clause, table_exists, with_limit
from daily_report.storage.repositories.annotation_repository import AnnotationRepository


class BrowserSourceAdapter(SourceAdapter):
    source_type = 'browser'

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
            if not table_exists(conn, 'browser_history_entries'):
                return []
            clauses = ['date = ?']
            params: list[Any] = [date]
            if selected is not None:
                clauses.append('is_selected = ?')
                params.append(int(selected))
            if not include_deleted:
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
                ORDER BY visit_time ASC, id ASC
                {limit_clause(limit)}
                """,
                tuple(with_limit(params, limit, offset)),
            ).fetchall()
            annotation_map = AnnotationRepository(conn).get_annotations_for_ids('browser', [int(row['id']) for row in rows])
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
            row = conn.execute('SELECT * FROM browser_history_entries WHERE id = ?', (int(source_id),)).fetchone()
            if row is None:
                return None
            data = dict(row)
            annotation = AnnotationRepository(conn).get_annotation('browser', int(source_id))
            data['annotation'] = dict(annotation) if annotation else None
            return data

    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        row = raw_event.raw
        annotation = row.get('annotation') or {}
        category = annotation.get('category') or infer_category_for_browser(
            row.get('title'), row.get('url'), row.get('is_search'), row.get('search_query')
        )
        title = str(row.get('title') or row.get('domain') or row.get('url') or '浏览记录')
        return TimelineEvent(
            event_id=f"browser:{raw_event.source_id}",
            source_type='browser',
            source_id=raw_event.source_id,
            start_time=str(row.get('visit_time') or ''),
            end_time=None,
            title=title,
            subtitle=str(row.get('domain') or ''),
            content_preview=str(row.get('search_query') or row.get('url') or ''),
            category=category,
            is_selected=bool(row.get('is_selected')),
            is_sensitive=bool(annotation.get('is_sensitive_override') or 0),
            is_deleted=bool(row.get('is_deleted')),
            raw=row,
        )

    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        row = event.raw or {}
        if bool(row.get('is_noise')) and not bool(row.get('is_search')):
            return None
        annotation = row.get('annotation') or {}
        if row.get('is_search'):
            title = f"搜索：{row.get('search_query') or row.get('title') or row.get('domain')}"
            summary = f"通过 {row.get('search_engine') or '搜索引擎'} 调研：{row.get('search_query') or ''}"
            evidence = str(row.get('search_query') or row.get('url') or '')
            importance = max(1, int(annotation.get('importance') or 0))
        else:
            title = event.title
            summary = f"浏览 {row.get('domain') or '网页'}：{title}"
            evidence = str(row.get('url') or title)
            importance = int(annotation.get('importance') or 0)
        return MaterialCard(
            source_type='browser',
            source_id=event.source_id,
            time_range=hhmm(event.start_time),
            category=event.category,
            title=make_preview(title, 120),
            summary=make_preview(summary, 180),
            evidence=make_preview(evidence, 220),
            importance=importance,
            is_sensitive=event.is_sensitive,
        )

    def update_selected(self, source_id: int, selected: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE browser_history_entries SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(selected), int(source_id)),
            )
            conn.commit()

    def update_deleted(self, source_id: int, deleted: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE browser_history_entries SET is_deleted = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(deleted), int(source_id)),
            )
            conn.commit()
