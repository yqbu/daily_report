from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from daily_report.sources.aliases import normalize_source_type, normalize_source_types
from daily_report.sources.base import TimelineEvent
from daily_report.sources.registry import SourceRegistry, create_default_source_registry
from daily_report.storage.database import default_db_path


SourceType = str


class TimelineService:
    def __init__(
        self,
        db_path: str | Path | None = None,
        registry: SourceRegistry | None = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.registry = registry or create_default_source_registry(self.db_path)

    def list_timeline(
        self,
        date: str | None = None,
        source_types: list[str] | None = None,
        selected: bool | None = None,
        sensitive: bool | None = None,
        category: str | list[str] | None = None,
        keyword: str | None = None,
        limit: int = 500,
        offset: int = 0,
        sort_order: str = 'asc',
    ) -> list[TimelineEvent]:
        day = date or date_cls.today().isoformat()
        wanted = normalize_source_types(source_types)
        start = max(0, int(offset or 0))
        stop = start + max(1, int(limit))
        query_limit = None if _requires_full_scan(wanted, sensitive, category) else stop

        events: list[TimelineEvent] = []
        for source_type in wanted:
            adapter = self.registry.get(source_type)
            raw_events = adapter.list_raw_by_date(
                date=day,
                selected=selected,
                sensitive=sensitive,
                keyword=str(keyword or '').strip() or None,
                include_deleted=False,
                limit=query_limit,
                offset=0,
            )
            source_events = [adapter.normalize(raw_event) for raw_event in raw_events]
            if source_type == 'app':
                source_events = _aggregate_app_events(source_events)
            events.extend(source_events)

        if sensitive is not None:
            events = [event for event in events if event.is_sensitive is sensitive]
        categories = _normalize_categories(category)
        if categories:
            events = [event for event in events if event.category in categories]

        reverse = sort_order.lower() == 'desc'
        events.sort(key=lambda event: (event.start_time or '', event.source_id), reverse=reverse)
        return events[start:stop]

    def update_entry_selection(self, source_type: str, source_id: int, selected: bool) -> None:
        self.registry.get(source_type).update_selected(source_id, selected)

    def update_entry_deleted(self, source_type: str, source_id: int, deleted: bool) -> None:
        self.registry.get(source_type).update_deleted(source_id, deleted)

    def mark_entry_deleted(self, source_type: str, source_id: int) -> None:
        self.update_entry_deleted(source_type, source_id, True)

    def get_entry_detail(
        self,
        source_type: str,
        source_id: int,
        source_ids: list[int] | None = None,
    ) -> dict[str, Any] | None:
        normalized = normalize_source_type(source_type)
        adapter = self.registry.get(normalized)
        data = adapter.get_raw_detail(source_id)
        if data is None:
            return None
        ids = [int(item) for item in (source_ids or []) if int(item) > 0]
        if normalized == 'app' and len(ids) > 1:
            data['source_ids'] = ids
            aggregate_items = []
            for item_id in ids:
                detail = adapter.get_raw_detail(item_id)
                if detail is not None:
                    aggregate_items.append(
                        {
                            key: detail.get(key)
                            for key in (
                                'id',
                                'app_name',
                                'process_name',
                                'window_title',
                                'start_time',
                                'end_time',
                                'duration_sec',
                                'active_duration_sec',
                            )
                        }
                    )
            data['aggregate_items'] = aggregate_items
            data['aggregate_count'] = len(aggregate_items)
        return data

    @classmethod
    def _normalize_source_types(cls, source_types: list[str] | None) -> set[str]:
        return set(normalize_source_types(source_types))

    @staticmethod
    def _normalize_source_type(source_type: str) -> SourceType:
        return normalize_source_type(source_type)

    @classmethod
    def _source_table(cls, source_type: str) -> str:
        mapping = {
            'app': 'app_sessions',
            'browser': 'browser_history_entries',
            'browser_event': 'browser_events',
            'clipboard': 'clipboard_entries',
            'ai_prompt': 'ai_prompt_entries',
        }
        return mapping[normalize_source_type(source_type)]


def _normalize_categories(value: str | list[str] | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        text = value.strip()
        return {text} if text else set()
    return {str(item).strip() for item in value if str(item).strip()}


def _requires_full_scan(
    source_types: list[str],
    sensitive: bool | None,
    category: str | list[str] | None,
) -> bool:
    if _normalize_categories(category):
        return True
    return sensitive is not None and bool(set(source_types) & {'app', 'browser'})


def _parse_datetime(value: str | None) -> datetime | None:
    text = str(value or '').strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace(' ', 'T'))
    except ValueError:
        return None


def _aggregate_app_events(events: list[TimelineEvent]) -> list[TimelineEvent]:
    if not events:
        return []
    gap_limit = timedelta(minutes=10)
    sorted_events = sorted(events, key=lambda item: (item.start_time or '', item.source_id))
    groups: list[list[TimelineEvent]] = []
    for event in sorted_events:
        if not groups:
            groups.append([event])
            continue
        previous = groups[-1][-1]
        previous_end = _parse_datetime(previous.end_time or previous.start_time)
        current_start = _parse_datetime(event.start_time)
        same_bucket = (
            previous.title == event.title
            and previous.category == event.category
            and previous.is_sensitive is event.is_sensitive
        )
        close_enough = (
            previous_end is not None
            and current_start is not None
            and current_start - previous_end <= gap_limit
        )
        if same_bucket and close_enough:
            groups[-1].append(event)
        else:
            groups.append([event])

    aggregated: list[TimelineEvent] = []
    for group in groups:
        if len(group) == 1:
            single = group[0]
            aggregated.append(
                TimelineEvent(
                    **{
                        **single.to_dict(),
                        'source_ids': [single.source_id],
                        'item_count': 1,
                        'aggregate_kind': None,
                        'raw': single.raw,
                    }
                )
            )
            continue
        first = group[0]
        last = group[-1]
        source_ids = [item.source_id for item in group]
        previews = [item.content_preview or item.subtitle for item in group if item.content_preview or item.subtitle]
        aggregated.append(
            TimelineEvent(
                event_id=f"app-group:{source_ids[0]}-{source_ids[-1]}",
                source_type='app',
                source_id=source_ids[0],
                source_ids=source_ids,
                item_count=len(group),
                aggregate_kind='app_session_group',
                start_time=first.start_time,
                end_time=last.end_time or last.start_time,
                title=first.title,
                subtitle=f"{len(group)} 条前台应用记录",
                content_preview=previews[-1] if previews else '',
                category=first.category,
                is_selected=any(item.is_selected for item in group),
                is_sensitive=first.is_sensitive,
                is_deleted=all(item.is_deleted for item in group),
                raw={'items': [item.raw for item in group if item.raw]},
            )
        )
    return aggregated
