from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from daily_report.api.deps import get_timeline_service
from daily_report.api.response import ApiError, ok
from daily_report.api.schemas import DeletedUpdateRequest, SelectionUpdateRequest
from daily_report.service.timeline_service import TimelineService
from daily_report.sources.aliases import normalize_source_type

router = APIRouter(prefix='/api/entries', tags=['entries'])


@router.get('/{source_type}')
def list_entries(
    source_type: str,
    date: str | None = Query(default=None),
    selected: bool | None = Query(default=None),
    sensitive: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        normalized = _normalize_source_type(source_type)
        fetch_limit = max(offset + limit, 1)
        events = service.list_timeline(
            date=date,
            source_types=[normalized],
            selected=selected,
            sensitive=sensitive,
            keyword=str(keyword or '').strip() or None,
            limit=fetch_limit,
            offset=0,
            sort_order='asc',
        )
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_SOURCE_TYPE', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to list entries', 'ENTRY_QUERY_FAILED', 500) from exc

    page_items = events[offset : offset + limit]
    return ok({'items': [event.to_dict() for event in page_items], 'total': len(events)})


@router.get('/{source_type}/{entry_id}')
def get_entry_detail(
    source_type: str,
    entry_id: int,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        normalized = _normalize_source_type(source_type)
        detail = service.get_entry_detail(normalized, entry_id)
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_SOURCE_TYPE', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to load entry detail', 'ENTRY_DETAIL_FAILED', 500) from exc
    if detail is None:
        raise ApiError('Entry not found', 'ENTRY_NOT_FOUND', 404)
    return ok({'source_type': normalized, 'id': entry_id, 'detail': detail})


@router.patch('/{source_type}/{entry_id}/selection')
def update_entry_selection(
    source_type: str,
    entry_id: int,
    payload: SelectionUpdateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        normalized = _normalize_source_type(source_type)
        service.update_entry_selection(normalized, entry_id, payload.selected)
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_SOURCE_TYPE', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to update entry selection', 'ENTRY_UPDATE_FAILED', 500) from exc
    return ok({'source_type': normalized, 'id': entry_id, 'selected': payload.selected})


@router.patch('/{source_type}/{entry_id}/deleted')
def update_entry_deleted(
    source_type: str,
    entry_id: int,
    payload: DeletedUpdateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        normalized = _normalize_source_type(source_type)
        service.update_entry_deleted(normalized, entry_id, payload.deleted)
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_SOURCE_TYPE', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to update entry deleted state', 'ENTRY_UPDATE_FAILED', 500) from exc
    return ok({'source_type': normalized, 'id': entry_id, 'deleted': payload.deleted})


def _normalize_source_type(source_type: str) -> str:
    return normalize_source_type(source_type)

