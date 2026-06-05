from __future__ import annotations

from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.service.category import infer_category_for_clipboard
from daily_report.service.sensitivity import make_preview
from daily_report.sources.base import RawEvent, SourceAdapter, TimelineEvent, hhmm, limit_clause, table_exists, with_limit
from daily_report.storage.repositories.annotation_repository import AnnotationRepository


class ClipboardSourceAdapter(SourceAdapter):
    source_type = 'clipboard'

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
            if not table_exists(conn, 'clipboard_entries'):
                return []
            clauses = ['date = ?']
            params: list[Any] = [date]
            if selected is not None:
                clauses.append('is_selected = ?')
                params.append(int(selected))
            if sensitive is not None:
                clauses.append('is_sensitive = ?')
                params.append(int(sensitive))
            if not include_deleted:
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
                ORDER BY first_seen_at ASC, id ASC
                {limit_clause(limit)}
                """,
                tuple(with_limit(params, limit, offset)),
            ).fetchall()
            annotation_map = AnnotationRepository(conn).get_annotations_for_ids('clipboard', [int(row['id']) for row in rows])
        raw_events = []
        for row in rows:
            data = dict(row)
            data['annotation'] = annotation_map.get(int(row['id']), {})
            raw_events.append(RawEvent(self.source_type, int(row['id']), data))
        return raw_events

    def get_raw_detail(self, source_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM clipboard_entries WHERE id = ?', (int(source_id),)).fetchone()
            if row is None:
                return None
            data = dict(row)
            annotation = AnnotationRepository(conn).get_annotation('clipboard', int(source_id))
            data['annotation'] = dict(annotation) if annotation else None
            return data

    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        row = raw_event.raw
        annotation = row.get('annotation') or {}
        category = annotation.get('category') or infer_category_for_clipboard(row.get('content_preview'))
        is_sensitive = bool(row.get('is_sensitive'))
        if annotation.get('is_sensitive_override') is not None:
            is_sensitive = bool(annotation.get('is_sensitive_override'))
        return TimelineEvent(
            event_id=f"clipboard:{raw_event.source_id}",
            source_type='clipboard',
            source_id=raw_event.source_id,
            start_time=str(row.get('first_seen_at') or row.get('last_seen_at') or ''),
            end_time=str(row.get('last_seen_at')) if row.get('last_seen_at') else None,
            title='剪切板文本',
            subtitle=f"{int(row.get('char_count') or 0)} 字",
            content_preview=str(row.get('content_preview') or ''),
            category=category,
            is_selected=bool(row.get('is_selected')),
            is_sensitive=is_sensitive,
            is_deleted=bool(row.get('is_deleted')),
            raw=row,
        )

    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        row = event.raw or {}
        annotation = row.get('annotation') or {}
        preview = str(row.get('content_preview') or event.content_preview or '')
        return MaterialCard(
            source_type='clipboard',
            source_id=event.source_id,
            time_range=hhmm(row.get('last_seen_at') or event.start_time),
            category=event.category,
            title='剪切板文本',
            summary=f"剪切板记录，约 {int(row.get('char_count') or len(preview))} 字。",
            evidence=make_preview(preview, 220),
            importance=int(annotation.get('importance') or 0),
            is_sensitive=event.is_sensitive,
        )

    def update_selected(self, source_id: int, selected: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE clipboard_entries SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(selected), int(source_id)),
            )
            conn.commit()

    def update_deleted(self, source_id: int, deleted: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE clipboard_entries SET is_deleted = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(deleted), int(source_id)),
            )
            conn.commit()
