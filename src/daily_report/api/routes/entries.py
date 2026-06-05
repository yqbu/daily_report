from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from daily_report.api.deps import get_timeline_service
from daily_report.api.response import ApiError, ok
from daily_report.api.schemas import (
    DeletedUpdateRequest,
    EntryKeyAnnotationUpdateRequest,
    EntryKeyDeletedUpdateRequest,
    EntryKeySelectionUpdateRequest,
    EntryKeySensitiveUpdateRequest,
    SelectionUpdateRequest,
)
from daily_report.service.timeline_service import TimelineService
from daily_report.sources.aliases import normalize_source_type

router = APIRouter(prefix='/api/entries', tags=['entries'])


@router.get('/by-key/{entry_key:path}')
def get_entry_detail_by_key(
    entry_key: str,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        detail = service.get_entry_detail_by_key(entry_key)
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_ENTRY_KEY', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to load entry detail', 'ENTRY_DETAIL_FAILED', 500) from exc
    if detail is None:
        raise ApiError('Entry not found', 'ENTRY_NOT_FOUND', 404)
    return ok({'entry_key': entry_key, 'detail': detail})


@router.patch('/by-key/selection')
def update_entry_selection_by_key(
    payload: EntryKeySelectionUpdateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        service.update_entry_selection_by_key(payload.entry_key, payload.selected)
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_ENTRY_KEY', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to update entry selection', 'ENTRY_UPDATE_FAILED', 500) from exc
    return ok({'entry_key': payload.entry_key, 'selected': payload.selected})


@router.patch('/by-key/deleted')
def update_entry_deleted_by_key(
    payload: EntryKeyDeletedUpdateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        service.update_entry_deleted_by_key(payload.entry_key, payload.deleted)
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_ENTRY_KEY', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to update entry deleted state', 'ENTRY_UPDATE_FAILED', 500) from exc
    return ok({'entry_key': payload.entry_key, 'deleted': payload.deleted})


@router.patch('/by-key/annotation')
def update_entry_annotation_by_key(
    payload: EntryKeyAnnotationUpdateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        annotation = service.update_entry_annotation_by_key(payload.entry_key, payload.dict(exclude={'entry_key'}))
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_ENTRY_KEY', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to update entry annotation', 'ENTRY_UPDATE_FAILED', 500) from exc
    return ok({'entry_key': payload.entry_key, 'annotation': annotation})


@router.patch('/by-key/sensitive')
def update_entry_sensitive_by_key(
    payload: EntryKeySensitiveUpdateRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> dict:
    try:
        annotation = service.update_entry_annotation_by_key(
            payload.entry_key,
            {
                'is_sensitive_override': payload.sensitive,
                'sensitivity_reason_override': payload.reason,
                'is_selected_override': False if payload.sensitive else None,
            },
        )
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_ENTRY_KEY', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to update entry sensitive state', 'ENTRY_UPDATE_FAILED', 500) from exc
    return ok({'entry_key': payload.entry_key, 'annotation': annotation})


@router.get('/{source_type}')
def list_entries(
    source_type: str,
    date: str | None = Query(default=None),
    selected: bool | None = Query(default=None),
    sensitive: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
    record_type: str | None = Query(default=None),
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
            record_type=_record_type_for_query(source_type, record_type),
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


def _record_type_for_query(source_type: str, record_type: str | None) -> str | None:
    explicit = str(record_type or '').strip()
    if explicit:
        return explicit
    if str(source_type or '').strip() in {'ai', 'ai_prompt'}:
        return 'ai_prompt'
    return None
