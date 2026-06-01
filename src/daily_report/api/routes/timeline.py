from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from daily_report.api.deps import get_timeline_service
from daily_report.api.response import ApiError, ok
from daily_report.service.timeline_service import TimelineService

router = APIRouter(prefix='/api', tags=['timeline'])


@router.get('/timeline')
def get_timeline(
    date: str | None = Query(default=None),
    source_type: str = Query(default='all'),
    selected: bool | None = Query(default=None),
    sensitive: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default='asc'),
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        source_types = _source_types(source_type)
        sort_order = _sort_order(order)
        fetch_limit = max(offset + limit, 1)
        events = service.list_timeline(
            date=date,
            source_types=source_types,
            selected=selected,
            sensitive=sensitive,
            keyword=str(keyword or '').strip() or None,
            limit=fetch_limit,
            offset=0,
            sort_order=sort_order,
        )
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_QUERY', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to query timeline', 'TIMELINE_QUERY_FAILED', 500) from exc

    page_items = events[offset : offset + limit]
    return ok({'items': [event.to_dict() for event in page_items], 'total': len(events)})


def _source_types(source_type: str) -> list[str] | None:
    normalized = str(source_type or 'all').strip()
    if normalized == 'all':
        return None
    if normalized == 'ai':
        normalized = 'ai_prompt'
    if normalized not in {'app', 'browser', 'clipboard', 'ai_prompt'}:
        raise ValueError(f'Unsupported source_type: {source_type}')
    return [normalized]


def _sort_order(order: str) -> str:
    normalized = str(order or 'asc').lower()
    if normalized not in {'asc', 'desc'}:
        raise ValueError(f'Unsupported order: {order}')
    return normalized

