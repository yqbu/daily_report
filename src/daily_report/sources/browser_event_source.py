from __future__ import annotations

import json
from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.domain.sensitivity import make_preview
from daily_report.sources.base import RawEvent, SourceAdapter, TimelineEvent, format_seconds, hhmm
from daily_report.storage.repositories.browser_event_repository import BrowserEventRepository


class BrowserEventSourceAdapter(SourceAdapter):
    source_type = 'browser_event'

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
        filters: dict[str, Any] = {
            'selected': selected,
            'sensitive': sensitive,
            'keyword': keyword,
            'record_type': record_type,
        }
        if not include_deleted:
            filters['deleted'] = False
        with self._connect() as conn:
            rows = BrowserEventRepository(conn).list_by_date(
                date=date,
                filters=filters,
                limit=limit or 100000,
                offset=offset,
            )
        return [RawEvent(self.source_type, int(row['id']), dict(row)) for row in rows]

    def get_raw_detail(self, source_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = BrowserEventRepository(conn).get_by_id(int(source_id))
        if row is None:
            return None
        data = dict(row)
        data['payload'] = _parse_payload(data.get('payload_json'))
        return data

    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        row = raw_event.raw
        event_type = str(row.get('event_type') or '')
        title = _event_title(row)
        duration = float(row.get('duration_sec') or 0)
        return TimelineEvent(
            event_id=f"browser_event:{raw_event.source_id}",
            source_type='browser_event',
            source_id=raw_event.source_id,
            start_time=str(row.get('timestamp') or ''),
            end_time=None,
            title=title,
            subtitle=_event_subtitle(row),
            content_preview=_event_preview(row),
            category=_event_category(event_type),
            is_selected=bool(row.get('is_selected')),
            is_sensitive=bool(row.get('is_sensitive')),
            is_deleted=bool(row.get('is_deleted')),
            raw={**row, 'duration_text': format_seconds(duration) if duration else ''},
        )

    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        row = event.raw or {}
        if event.is_sensitive or not event.is_selected or event.is_deleted:
            return None
        event_type = str(row.get('event_type') or '')
        if event_type == 'search':
            query = str(row.get('search_query') or event.content_preview or '').strip()
            if not query:
                return None
            engine = str(row.get('search_engine') or row.get('domain') or 'search')
            return MaterialCard(
                source_type='browser_event',
                source_id=event.source_id,
                time_range=hhmm(event.start_time),
                category=event.category,
                title=make_preview(f'搜索: {query}', 120),
                summary=make_preview(f'通过 {engine} 搜索调研: {query}', 180),
                evidence=make_preview(str(row.get('url') or query), 220),
                importance=1,
                is_sensitive=False,
            )
        if event_type == 'copy':
            preview = str(row.get('content_preview') or '').strip()
            if not preview:
                return None
            return MaterialCard(
                source_type='browser_event',
                source_id=event.source_id,
                time_range=hhmm(event.start_time),
                category=event.category,
                title='网页复制片段',
                summary=make_preview(f'从 {row.get("domain") or "网页"} 复制了一段资料', 180),
                evidence=make_preview(preview, 220),
                importance=0,
                is_sensitive=False,
            )
        if event_type == 'dwell_time' and float(row.get('duration_sec') or 0) >= 300:
            title = str(row.get('title') or row.get('domain') or '网页停留')
            return MaterialCard(
                source_type='browser_event',
                source_id=event.source_id,
                time_range=hhmm(event.start_time),
                category=event.category,
                title=make_preview(title, 120),
                summary=make_preview(f'在 {row.get("domain") or "网页"} 停留 {event.raw.get("duration_text")}', 180),
                evidence=make_preview(str(row.get('url') or title), 220),
                importance=0,
                is_sensitive=False,
            )
        return None

    def update_selected(self, source_id: int, selected: bool) -> None:
        with self._connect() as conn:
            BrowserEventRepository(conn).update_selected(int(source_id), selected)

    def update_deleted(self, source_id: int, deleted: bool) -> None:
        with self._connect() as conn:
            BrowserEventRepository(conn).update_deleted(int(source_id), deleted)


def _event_title(row: dict[str, Any]) -> str:
    event_type = str(row.get('event_type') or '')
    if event_type == 'search':
        return f"搜索: {row.get('search_query') or row.get('title') or row.get('domain') or ''}".strip()
    if event_type == 'copy':
        return '网页复制'
    if event_type == 'dwell_time':
        return f"网页停留: {row.get('title') or row.get('domain') or ''}".strip()
    if event_type == 'ai_prompt_submit':
        return 'AI 提问提交'
    return str(row.get('title') or _event_type_label(event_type) or row.get('domain') or '浏览器事件')


def _event_subtitle(row: dict[str, Any]) -> str:
    parts = [str(row.get('domain') or '').strip(), _event_type_label(str(row.get('event_type') or ''))]
    return ' · '.join(part for part in parts if part)


def _event_preview(row: dict[str, Any]) -> str:
    event_type = str(row.get('event_type') or '')
    if event_type == 'search':
        return str(row.get('search_query') or row.get('url') or '')
    if event_type == 'copy':
        return str(row.get('content_preview') or '')
    if event_type == 'dwell_time':
        return f"{format_seconds(float(row.get('duration_sec') or 0))} · {row.get('url') or ''}"
    return str(row.get('content_preview') or row.get('url') or row.get('title') or '')


def _event_category(event_type: str) -> str:
    if event_type in {'search', 'copy', 'dwell_time'}:
        return '资料调研'
    if event_type == 'ai_prompt_submit':
        return 'AI 辅助'
    return '其他'


def _event_type_label(event_type: str) -> str:
    return {
        'page_view': '页面访问',
        'tab_active': '标签激活',
        'tab_inactive': '标签失焦',
        'page_leave': '页面离开',
        'dwell_time': '停留时长',
        'search': '搜索',
        'copy': '复制',
        'ai_prompt_submit': 'AI 提问',
    }.get(event_type, event_type)


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
