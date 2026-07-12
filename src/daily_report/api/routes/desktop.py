from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter

from daily_report.api.response import ApiError, ok
from daily_report.service.desktop_service import DesktopService

router = APIRouter(prefix='/api/desktop', tags=['desktop'])


@router.post('/{method}')
def call_desktop_method(method: str, payload: dict[str, Any] | None = None) -> dict:
    service = DesktopService()
    data = payload or {}
    handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
        'getOverview': lambda params: service.get_overview(_date_arg(params)),
        'getTimeline': service.get_timeline,
        'getEntryDetail': lambda params: _get_entry_detail(service, params),
        'updateEntrySelection': lambda params: _update_entry_selection(service, params),
        'markEntryDeleted': lambda params: _mark_entry_deleted(service, params),
        'updateEntryAnnotation': lambda params: _update_entry_annotation(service, params),
        'updateEntrySensitive': lambda params: _update_entry_sensitive(service, params),
        'getDataCenterSummary': service.get_data_center_summary,
        'getDataCenterAnalytics': service.get_data_center_analytics,
        'listAppProfiles': service.list_app_profiles,
        'extractAppProfiles': service.extract_app_profiles,
        'saveAppProfile': service.save_app_profile,
        'resetAppProfile': service.reset_app_profile,
        'deleteAppRecords': service.delete_app_records,
        'listAppCategories': service.list_app_categories,
        'saveAppCategory': service.save_app_category,
        'deleteAppCategory': service.delete_app_category,
        'getReportMaterials': service.get_report_materials,
        'batchUpdateEntrySelection': service.batch_update_entry_selection,
        'buildPrompt': service.build_prompt,
        'generateReport': service.generate_report_sync,
        'saveReport': service.save_report,
        'listReports': service.list_reports,
        'getReportDetail': service.get_report_detail_by_id,
        'deleteReport': service.delete_report_by_id,
        'test_model_connection': service.test_model_connection,
    }

    if method == 'getLatestReport':
        handlers[method] = lambda params: service.get_latest_report(_date_arg(params))

    handler = handlers.get(method)
    if handler is None:
        raise ApiError(f'Unsupported desktop API method: {method}', 'UNSUPPORTED_DESKTOP_METHOD', 404)

    try:
        return ok(handler(data))
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_DESKTOP_REQUEST', 400) from exc
    except Exception as exc:
        raise ApiError(f'Desktop API method failed: {method}', 'DESKTOP_METHOD_FAILED', 500) from exc


def _date_arg(data: dict[str, Any]) -> str | None:
    return str(data.get('date') or '').strip() or None


def _source_type(data: dict[str, Any]) -> str:
    return str(data.get('sourceType') or data.get('source_type') or '')


def _entry_id(data: dict[str, Any]) -> int:
    return int(data.get('id') or data.get('source_id') or 0)


def _entry_key(data: dict[str, Any]) -> str | None:
    return str(data.get('entryKey') or data.get('entry_key') or '').strip() or None


def _source_ids(data: dict[str, Any]) -> list[int] | None:
    raw_ids = data.get('ids') or data.get('sourceIds') or data.get('source_ids')
    return [int(item) for item in raw_ids] if isinstance(raw_ids, list) else None


def _get_entry_detail(service: DesktopService, data: dict[str, Any]) -> dict[str, Any] | None:
    return service.get_entry_detail(
        _source_type(data),
        _entry_id(data),
        _source_ids(data),
        _entry_key(data),
    )


def _update_entry_selection(service: DesktopService, data: dict[str, Any]) -> dict[str, Any]:
    return service.update_entry_selection(
        _source_type(data),
        _entry_id(data),
        bool(data.get('selected')),
        _source_ids(data),
        _entry_key(data),
    )


def _mark_entry_deleted(service: DesktopService, data: dict[str, Any]) -> dict[str, Any]:
    return service.mark_entry_deleted(_source_type(data), _entry_id(data), _entry_key(data))


def _update_entry_annotation(service: DesktopService, data: dict[str, Any]) -> dict[str, Any]:
    return service.update_entry_annotation(
        _source_type(data),
        _entry_id(data),
        data.get('payload') if isinstance(data.get('payload'), dict) else {},
        _entry_key(data),
    )


def _update_entry_sensitive(service: DesktopService, data: dict[str, Any]) -> dict[str, Any]:
    return service.update_entry_sensitive(
        _source_type(data),
        _entry_id(data),
        bool(data.get('sensitive')),
        str(data.get('reason') or '').strip() or None,
        _source_ids(data),
        _entry_key(data),
    )
