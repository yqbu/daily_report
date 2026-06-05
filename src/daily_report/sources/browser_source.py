from __future__ import annotations

import json
from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.service.category import infer_category_for_ai_prompt, infer_category_for_browser
from daily_report.service.sensitivity import make_preview
from daily_report.sources.base import RawEvent, SourceAdapter, TimelineEvent, format_seconds, hhmm, limit_clause, table_exists, with_limit
from daily_report.storage.repositories.annotation_repository import AnnotationRepository
from daily_report.storage.repositories.browser_event_repository import BrowserEventRepository
from daily_report.storage.repositories.entry_annotation_v2_repository import EntryAnnotationV2Repository

BROWSER_RECORD_TYPES = {
    'history_visit',
    'search',
    'page_view',
    'dwell_time',
    'copy',
    'ai_prompt',
    'tab_active',
    'tab_inactive',
    'page_leave',
}


class BrowserSourceAdapter(SourceAdapter):
    source_type = 'browser'

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
        wanted_record_types = _record_type_filter(record_type)
        raw_events: list[RawEvent] = []
        with self._connect() as conn:
            if _wants(wanted_record_types, {'history_visit', 'search'}) and table_exists(conn, 'browser_history_entries'):
                raw_events.extend(
                    self._list_history_rows(
                        conn,
                        date=date,
                        selected=selected,
                        sensitive=sensitive,
                        keyword=keyword,
                        record_types=wanted_record_types,
                        include_deleted=include_deleted,
                    )
                )
            if _wants(wanted_record_types, {'ai_prompt'}) and table_exists(conn, 'ai_prompt_entries'):
                raw_events.extend(
                    self._list_legacy_ai_prompt_rows(
                        conn,
                        date=date,
                        selected=selected,
                        sensitive=sensitive,
                        keyword=keyword,
                        include_deleted=include_deleted,
                    )
                )
            if _wants(wanted_record_types, BROWSER_RECORD_TYPES) and table_exists(conn, 'browser_events'):
                raw_events.extend(
                    self._list_browser_event_rows(
                        conn,
                        date=date,
                        selected=selected,
                        sensitive=sensitive,
                        keyword=keyword,
                        record_type=record_type,
                        include_deleted=include_deleted,
                    )
                )

        raw_events.sort(key=lambda item: (_timestamp_for_sort(item.raw), item.raw.get('origin_source_type') or '', item.source_id))
        start = max(0, int(offset or 0))
        stop = None if limit is None else start + max(1, int(limit))
        return raw_events[start:stop]

    def get_raw_detail(self, source_id: int) -> dict[str, Any] | None:
        return self.get_raw_detail_by_entry_key(f'browser:history:{source_id}')

    def get_raw_detail_by_entry_key(self, entry_key: str) -> dict[str, Any] | None:
        parsed = _parse_browser_entry_key(entry_key)
        if parsed is None:
            return None
        origin, source_id = parsed
        with self._connect() as conn:
            if origin == 'history':
                row = conn.execute('SELECT * FROM browser_history_entries WHERE id = ?', (source_id,)).fetchone()
                return self._detail_from_row(conn, row, 'history') if row else None
            if origin == 'ai_prompt':
                row = conn.execute('SELECT * FROM ai_prompt_entries WHERE id = ?', (source_id,)).fetchone()
                return self._detail_from_row(conn, row, 'ai_prompt') if row else None
            if origin == 'event':
                row = BrowserEventRepository(conn).get_by_id(source_id)
                return self._detail_from_row(conn, row, 'event') if row else None
        return None

    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        row = raw_event.raw
        origin = str(row.get('origin_source_type') or '')
        record_type = str(row.get('record_type') or 'history_visit')
        entry_key = str(row.get('entry_key') or f'browser:{origin}:{raw_event.source_id}')
        annotation = row.get('annotation_v2') or {}
        legacy_annotation = row.get('annotation') or {}
        category = _annotation_value(annotation, legacy_annotation, 'category') or _default_category(record_type)
        importance = _importance(row, annotation)
        is_selected = _selected(row, annotation)
        is_sensitive = _sensitive(row, annotation, legacy_annotation)

        if origin == 'ai_prompt':
            platform = str(row.get('platform') or 'AI')
            title = f'{platform} 提问'
            subtitle = str(row.get('page_title') or row.get('conversation_url') or '')
            preview = str(row.get('prompt_preview') or '')
            start_time = str(row.get('timestamp') or '')
        elif origin == 'event':
            title = _browser_event_title(row)
            subtitle = _browser_event_subtitle(row)
            preview = _browser_event_preview(row)
            start_time = str(row.get('timestamp') or '')
        else:
            title = str(row.get('title') or row.get('domain') or row.get('url') or '浏览器记录')
            subtitle = str(row.get('domain') or '')
            preview = str(row.get('search_query') or row.get('url') or '')
            start_time = str(row.get('visit_time') or '')

        return TimelineEvent(
            event_id=entry_key,
            source_type='browser',
            source_id=raw_event.source_id,
            start_time=start_time,
            end_time=None,
            title=title,
            subtitle=subtitle,
            content_preview=preview,
            category=str(category),
            is_selected=is_selected,
            is_sensitive=is_sensitive,
            is_deleted=bool(row.get('is_deleted')),
            record_type=record_type,
            entry_key=entry_key,
            importance=importance,
            origin_source_type={'history': 'browser_history', 'ai_prompt': 'ai_prompt', 'event': 'browser_event'}.get(origin, origin),
            origin_source_id=raw_event.source_id,
            raw=row,
        )

    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        row = event.raw or {}
        record_type = event.record_type or str(row.get('record_type') or '')
        if event.is_sensitive or event.is_deleted or not event.is_selected:
            return None
        if record_type in {'page_view', 'tab_active', 'tab_inactive', 'page_leave'} and event.importance < 50:
            return None
        if record_type == 'dwell_time' and (event.importance < 50 or float(row.get('duration_sec') or 0) < 60):
            return None
        if record_type == 'history_visit' and event.importance < 50 and not bool(row.get('is_selected')):
            return None

        title, summary, evidence = _material_text(event, row, record_type)
        return MaterialCard(
            source_type='browser',
            source_id=event.source_id,
            time_range=hhmm(event.start_time),
            category=event.category,
            title=make_preview(title, 120),
            summary=make_preview(summary, 180),
            evidence=make_preview(evidence, 220),
            importance=event.importance,
            is_sensitive=event.is_sensitive,
            record_type=record_type,
            entry_key=event.entry_key,
        )

    def update_selected(self, source_id: int, selected: bool) -> None:
        self.update_selected_by_entry_key(f'browser:history:{source_id}', selected)

    def update_deleted(self, source_id: int, deleted: bool) -> None:
        self.update_deleted_by_entry_key(f'browser:history:{source_id}', deleted)

    def update_selected_by_entry_key(self, entry_key: str, selected: bool) -> None:
        parsed = _parse_browser_entry_key(entry_key)
        if parsed is None:
            raise ValueError(f'Unsupported browser entry_key: {entry_key}')
        origin, source_id = parsed
        with self._connect() as conn:
            if origin == 'history':
                conn.execute(
                    "UPDATE browser_history_entries SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (int(selected), source_id),
                )
            elif origin == 'ai_prompt':
                conn.execute(
                    "UPDATE ai_prompt_entries SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (int(selected), source_id),
                )
            else:
                BrowserEventRepository(conn).update_selected(source_id, selected)
            EntryAnnotationV2Repository(conn).upsert_annotation(
                entry_key=entry_key,
                source_type='browser',
                record_type=self._record_type_for_key(conn, entry_key),
                is_selected_override=selected,
            )
            conn.commit()

    def update_deleted_by_entry_key(self, entry_key: str, deleted: bool) -> None:
        parsed = _parse_browser_entry_key(entry_key)
        if parsed is None:
            raise ValueError(f'Unsupported browser entry_key: {entry_key}')
        origin, source_id = parsed
        with self._connect() as conn:
            if origin == 'history':
                conn.execute(
                    "UPDATE browser_history_entries SET is_deleted = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (int(deleted), source_id),
                )
            elif origin == 'ai_prompt':
                conn.execute(
                    "UPDATE ai_prompt_entries SET is_deleted = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (int(deleted), source_id),
                )
            else:
                BrowserEventRepository(conn).update_deleted(source_id, deleted)
            conn.commit()

    def update_annotation_by_entry_key(self, entry_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            row = EntryAnnotationV2Repository(conn).upsert_annotation(
                entry_key=entry_key,
                source_type='browser',
                record_type=self._record_type_for_key(conn, entry_key),
                category=payload.get('category'),
                note=payload.get('note'),
                importance=payload.get('importance'),
                is_selected_override=_optional_bool(payload.get('is_selected_override')),
                is_sensitive_override=_optional_bool(payload.get('is_sensitive_override')),
                sensitivity_reason_override=payload.get('sensitivity_reason_override'),
            )
            parsed = _parse_browser_entry_key(entry_key)
            if parsed and parsed[0] == 'event' and payload.get('importance') is not None:
                conn.execute(
                    "UPDATE browser_events SET importance = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (max(0, min(100, int(payload.get('importance') or 0))), parsed[1]),
                )
                conn.commit()
            return dict(row)

    def _record_type_for_key(self, conn, entry_key: str) -> str | None:
        detail = self._detail_from_row_for_key(conn, entry_key)
        return str(detail.get('record_type') or '') if detail else None

    def _detail_from_row_for_key(self, conn, entry_key: str) -> dict[str, Any] | None:
        parsed = _parse_browser_entry_key(entry_key)
        if parsed is None:
            return None
        origin, source_id = parsed
        if origin == 'history':
            row = conn.execute('SELECT * FROM browser_history_entries WHERE id = ?', (source_id,)).fetchone()
        elif origin == 'ai_prompt':
            row = conn.execute('SELECT * FROM ai_prompt_entries WHERE id = ?', (source_id,)).fetchone()
        else:
            row = BrowserEventRepository(conn).get_by_id(source_id)
        return self._detail_from_row(conn, row, origin) if row else None

    def _detail_from_row(self, conn, row, origin: str) -> dict[str, Any]:
        data = dict(row)
        data.update(_origin_metadata(origin, int(data.get('id') or 0), data))
        data['annotation_v2'] = _annotation_v2(conn, data['entry_key'])
        data['annotation'] = _legacy_annotation(conn, origin, int(data.get('id') or 0))
        if data.get('payload_json'):
            data['payload'] = _parse_payload(data.get('payload_json'))
        normalized = self.normalize(RawEvent('browser', int(data.get('id') or 0), data))
        merged = {**data, **normalized.to_dict()}
        merged['annotation'] = data.get('annotation_v2') or data.get('annotation')
        return merged

    def _list_history_rows(self, conn, **kwargs: Any) -> list[RawEvent]:
        date = kwargs['date']
        record_types = kwargs['record_types']
        selected = kwargs['selected']
        keyword = kwargs['keyword']
        include_deleted = kwargs['include_deleted']
        clauses = ['date = ?']
        params: list[Any] = [date]
        if record_types == {'search'}:
            clauses.append('is_search = 1')
        elif record_types == {'history_visit'}:
            clauses.append('is_search = 0')
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
            {limit_clause(None)}
            """,
            tuple(with_limit(params, None, 0)),
        ).fetchall()
        events = []
        for row in rows:
            data = dict(row)
            data.update(_origin_metadata('history', int(row['id']), data))
            data['annotation_v2'] = _annotation_v2(conn, data['entry_key'])
            data['annotation'] = _legacy_annotation(conn, 'history', int(row['id']))
            if not _passes_sensitive(data, kwargs['sensitive']):
                continue
            events.append(RawEvent('browser', int(row['id']), data))
        return events

    def _list_legacy_ai_prompt_rows(self, conn, **kwargs: Any) -> list[RawEvent]:
        clauses = ['date = ?']
        params: list[Any] = [kwargs['date']]
        if kwargs['selected'] is not None:
            clauses.append('is_selected = ?')
            params.append(int(kwargs['selected']))
        if kwargs['sensitive'] is not None:
            clauses.append('is_sensitive = ?')
            params.append(int(kwargs['sensitive']))
        if not kwargs['include_deleted']:
            clauses.append('is_deleted = 0')
        if kwargs['keyword']:
            like = f"%{kwargs['keyword']}%"
            clauses.append('(prompt_preview LIKE ? OR prompt_text LIKE ? OR page_title LIKE ? OR platform LIKE ?)')
            params.extend([like, like, like, like])
        rows = conn.execute(
            f"""
            SELECT *
            FROM ai_prompt_entries
            WHERE {' AND '.join(clauses)}
            ORDER BY timestamp ASC, id ASC
            """,
            tuple(params),
        ).fetchall()
        events = []
        for row in rows:
            data = dict(row)
            data.update(_origin_metadata('ai_prompt', int(row['id']), data))
            data['annotation_v2'] = _annotation_v2(conn, data['entry_key'])
            data['annotation'] = _legacy_annotation(conn, 'ai_prompt', int(row['id']))
            events.append(RawEvent('browser', int(row['id']), data))
        return events

    def _list_browser_event_rows(self, conn, **kwargs: Any) -> list[RawEvent]:
        filters: dict[str, Any] = {
            'selected': kwargs['selected'],
            'sensitive': kwargs['sensitive'],
            'keyword': kwargs['keyword'],
        }
        if kwargs['record_type']:
            filters['record_type'] = kwargs['record_type']
        if not kwargs['include_deleted']:
            filters['deleted'] = False
        rows = BrowserEventRepository(conn).list_by_date(kwargs['date'], filters=filters, limit=100000, offset=0)
        events = []
        for row in rows:
            data = dict(row)
            data.update(_origin_metadata('event', int(row['id']), data))
            data['annotation_v2'] = _annotation_v2(conn, data['entry_key'])
            events.append(RawEvent('browser', int(row['id']), data))
        return events


def _origin_metadata(origin: str, source_id: int, row: dict[str, Any]) -> dict[str, Any]:
    if origin == 'history':
        record_type = 'search' if bool(row.get('is_search')) else 'history_visit'
        return {
            'origin_source_type': 'history',
            'record_type': record_type,
            'entry_key': f'browser:history:{source_id}',
        }
    if origin == 'ai_prompt':
        return {
            'origin_source_type': 'ai_prompt',
            'record_type': 'ai_prompt',
            'entry_key': f'browser:ai_prompt:{source_id}',
        }
    record_type = str(row.get('record_type') or row.get('event_type') or 'page_view')
    if record_type == 'ai_prompt_submit':
        record_type = 'ai_prompt'
    return {
        'origin_source_type': 'event',
        'record_type': record_type,
        'entry_key': f'browser:event:{source_id}',
    }


def _annotation_v2(conn, entry_key: str) -> dict[str, Any]:
    row = EntryAnnotationV2Repository(conn).get_by_entry_key(entry_key)
    return dict(row) if row else {}


def _legacy_annotation(conn, origin: str, source_id: int) -> dict[str, Any]:
    source_type = {'history': 'browser', 'ai_prompt': 'ai_prompt'}.get(origin)
    if not source_type:
        return {}
    row = AnnotationRepository(conn).get_annotation(source_type, source_id)
    return dict(row) if row else {}


def _record_type_filter(record_type: str | None) -> set[str] | None:
    text = str(record_type or '').strip()
    if not text:
        return None
    if text == 'ai_prompt_submit':
        text = 'ai_prompt'
    if text not in BROWSER_RECORD_TYPES:
        return {text}
    return {text}


def _wants(wanted: set[str] | None, candidates: set[str]) -> bool:
    return wanted is None or bool(wanted & candidates)


def _passes_sensitive(row: dict[str, Any], sensitive: bool | None) -> bool:
    if sensitive is None:
        return True
    return _sensitive(row, row.get('annotation_v2') or {}, row.get('annotation') or {}) is sensitive


def _selected(row: dict[str, Any], annotation: dict[str, Any]) -> bool:
    if annotation.get('is_selected_override') is not None:
        return bool(annotation.get('is_selected_override'))
    record_type = str(row.get('record_type') or '')
    if record_type in {'ai_prompt', 'search'} and not bool(row.get('is_sensitive')):
        return bool(row.get('is_selected', 1))
    return bool(row.get('is_selected'))


def _sensitive(row: dict[str, Any], annotation: dict[str, Any], legacy_annotation: dict[str, Any]) -> bool:
    if annotation.get('is_sensitive_override') is not None:
        return bool(annotation.get('is_sensitive_override'))
    if legacy_annotation.get('is_sensitive_override') is not None:
        return bool(legacy_annotation.get('is_sensitive_override'))
    return bool(row.get('is_sensitive'))


def _importance(row: dict[str, Any], annotation: dict[str, Any]) -> int:
    if annotation:
        return max(0, min(100, int(annotation.get('importance') or 0)))
    record_type = str(row.get('record_type') or '')
    if record_type == 'ai_prompt':
        return 90
    if record_type == 'search':
        return 70
    if record_type == 'copy':
        return 50
    if record_type == 'dwell_time':
        duration = float(row.get('duration_sec') or 0)
        if duration > 300:
            return 50
        if duration >= 60:
            return 30
        return 10
    if record_type == 'history_visit':
        return 10 if bool(row.get('is_noise')) else 30
    if record_type == 'page_view':
        return 10
    return int(row.get('importance') or 0)


def _annotation_value(annotation: dict[str, Any], legacy_annotation: dict[str, Any], key: str) -> Any:
    return annotation.get(key) if annotation.get(key) is not None else legacy_annotation.get(key)


def _default_category(record_type: str) -> str:
    return 'AI 辅助' if record_type == 'ai_prompt' else '资料调研' if record_type in {'search', 'history_visit', 'page_view', 'copy', 'dwell_time'} else '其他'


def _browser_event_title(row: dict[str, Any]) -> str:
    record_type = str(row.get('record_type') or '')
    if record_type == 'search':
        return f"搜索: {row.get('search_query') or row.get('title') or row.get('domain') or ''}".strip()
    if record_type == 'copy':
        return '网页复制'
    if record_type == 'dwell_time':
        return f"页面停留: {row.get('title') or row.get('domain') or ''}".strip()
    if record_type == 'ai_prompt':
        return 'AI 提问'
    return str(row.get('title') or _record_type_label(record_type) or row.get('domain') or '浏览器事件')


def _browser_event_subtitle(row: dict[str, Any]) -> str:
    parts = [str(row.get('domain') or '').strip(), _record_type_label(str(row.get('record_type') or ''))]
    return ' / '.join(part for part in parts if part)


def _browser_event_preview(row: dict[str, Any]) -> str:
    record_type = str(row.get('record_type') or '')
    if record_type == 'search':
        return str(row.get('search_query') or row.get('url') or '')
    if record_type == 'dwell_time':
        return f"{format_seconds(float(row.get('duration_sec') or 0))} / {row.get('url') or ''}"
    return str(row.get('content_preview') or row.get('search_query') or row.get('url') or row.get('title') or '')


def _record_type_label(record_type: str) -> str:
    return {
        'history_visit': '访问',
        'page_view': '访问',
        'search': '搜索',
        'dwell_time': '停留',
        'copy': '复制',
        'ai_prompt': 'AI 提问',
        'tab_active': '激活',
        'tab_inactive': '失焦',
        'page_leave': '离开',
    }.get(record_type, record_type)


def _material_text(event: TimelineEvent, row: dict[str, Any], record_type: str) -> tuple[str, str, str]:
    if record_type == 'ai_prompt':
        preview = str(row.get('prompt_preview') or row.get('content_preview') or event.content_preview or '')
        platform = str(row.get('platform') or 'AI')
        return f'{platform} 提问', f'向 {platform} 提问: {make_preview(preview, 160)}', preview
    if record_type == 'search':
        query = str(row.get('search_query') or event.content_preview or event.title)
        engine = str(row.get('search_engine') or row.get('domain') or '搜索引擎')
        return f'搜索: {query}', f'通过 {engine} 搜索调研: {query}', str(row.get('url') or query)
    if record_type == 'copy':
        preview = str(row.get('content_preview') or event.content_preview or '')
        return '网页复制片段', f'从 {row.get("domain") or "网页"} 复制了一段资料', preview
    if record_type == 'dwell_time':
        title = str(row.get('title') or row.get('domain') or event.title)
        return title, f'在 {row.get("domain") or "网页"} 停留 {format_seconds(float(row.get("duration_sec") or 0))}', str(row.get('url') or title)
    return event.title, f'浏览 {row.get("domain") or "网页"}: {event.title}', str(row.get('url') or event.content_preview or event.title)


def _parse_browser_entry_key(entry_key: str) -> tuple[str, int] | None:
    parts = str(entry_key or '').split(':')
    if len(parts) != 3 or parts[0] != 'browser':
        return None
    if parts[1] not in {'history', 'ai_prompt', 'event'}:
        return None
    try:
        source_id = int(parts[2])
    except ValueError:
        return None
    return parts[1], source_id


def _parse_payload(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not value:
        return None
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _timestamp_for_sort(row: dict[str, Any]) -> str:
    return str(row.get('visit_time') or row.get('timestamp') or row.get('created_at') or '')


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {'true', '1', 'yes', 'selected'}:
        return True
    if text in {'false', '0', 'no', 'unselected'}:
        return False
    return None
