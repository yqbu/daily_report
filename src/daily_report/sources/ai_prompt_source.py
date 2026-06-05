from __future__ import annotations

from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.service.category import infer_category_for_ai_prompt
from daily_report.service.sensitivity import make_preview
from daily_report.sources.base import RawEvent, SourceAdapter, TimelineEvent, hhmm, limit_clause, table_exists, with_limit
from daily_report.storage.repositories.annotation_repository import AnnotationRepository


class AIPromptSourceAdapter(SourceAdapter):
    source_type = 'ai_prompt'

    def list_raw_by_date(
        self,
        date: str,
        selected: bool | None = None,
        sensitive: bool | None = None,
        keyword: str | None = None,
        record_type: str | None = None,
        include_deleted: bool = False,
        limit: int | None = 500,
        offset: int = 0,
    ) -> list[RawEvent]:
        with self._connect() as conn:
            if not table_exists(conn, 'ai_prompt_entries'):
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
                clauses.append('(prompt_preview LIKE ? OR prompt_text LIKE ? OR page_title LIKE ? OR platform LIKE ?)')
                params.extend([like, like, like, like])
            rows = conn.execute(
                f"""
                SELECT *
                FROM ai_prompt_entries
                WHERE {' AND '.join(clauses)}
                ORDER BY timestamp ASC, id ASC
                {limit_clause(limit)}
                """,
                tuple(with_limit(params, limit, offset)),
            ).fetchall()
            annotation_map = AnnotationRepository(conn).get_annotations_for_ids('ai_prompt', [int(row['id']) for row in rows])
        raw_events = []
        for row in rows:
            data = dict(row)
            data['annotation'] = annotation_map.get(int(row['id']), {})
            raw_events.append(RawEvent(self.source_type, int(row['id']), data))
        return raw_events

    def get_raw_detail(self, source_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM ai_prompt_entries WHERE id = ?', (int(source_id),)).fetchone()
            if row is None:
                return None
            data = dict(row)
            annotation = AnnotationRepository(conn).get_annotation('ai_prompt', int(source_id))
            data['annotation'] = dict(annotation) if annotation else None
            return data

    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        row = raw_event.raw
        annotation = row.get('annotation') or {}
        category = annotation.get('category') or infer_category_for_ai_prompt(row.get('prompt_preview'))
        platform = str(row.get('platform') or 'AI')
        is_sensitive = bool(row.get('is_sensitive'))
        if annotation.get('is_sensitive_override') is not None:
            is_sensitive = bool(annotation.get('is_sensitive_override'))
        return TimelineEvent(
            event_id=f"ai_prompt:{raw_event.source_id}",
            source_type='ai_prompt',
            source_id=raw_event.source_id,
            start_time=str(row.get('timestamp') or ''),
            end_time=None,
            title=f'{platform} 提问',
            subtitle=str(row.get('page_title') or row.get('conversation_url') or ''),
            content_preview=str(row.get('prompt_preview') or ''),
            category=category,
            is_selected=bool(row.get('is_selected')),
            is_sensitive=is_sensitive,
            is_deleted=bool(row.get('is_deleted')),
            raw=row,
        )

    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        row = event.raw or {}
        annotation = row.get('annotation') or {}
        preview = str(row.get('prompt_preview') or event.content_preview or '')
        platform = str(row.get('platform') or 'AI')
        return MaterialCard(
            source_type='ai_prompt',
            source_id=event.source_id,
            time_range=hhmm(row.get('timestamp') or event.start_time),
            category=event.category,
            title=f'{platform} 提问',
            summary=f"向 {platform} 提问：{make_preview(preview, 160)}",
            evidence=make_preview(preview, 240),
            importance=max(1, int(annotation.get('importance') or 0)),
            is_sensitive=event.is_sensitive,
        )

    def update_selected(self, source_id: int, selected: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE ai_prompt_entries SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(selected), int(source_id)),
            )
            conn.commit()

    def update_deleted(self, source_id: int, deleted: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE ai_prompt_entries SET is_deleted = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(deleted), int(source_id)),
            )
            conn.commit()
