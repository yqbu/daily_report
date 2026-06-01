from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter

from daily_report.api.response import ApiError, ok
from daily_report.gui.services.gui_service import GuiService

router = APIRouter(prefix='/api/gui', tags=['gui'])


@router.post('/{method}')
def call_gui_method(method: str, payload: dict[str, Any] | None = None) -> dict:
    service = GuiService()
    data = payload or {}
    handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
        'getTimeline': service.get_timeline,
        'getDataCenterSummary': service.get_data_center_summary,
        'getDataCenterAnalytics': service.get_data_center_analytics,
        'listAppProfiles': service.list_app_profiles,
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
        return ok(service.get_latest_report(_date_arg(data)))
    if method == 'updateEntryAnnotation':
        return ok(
            service.update_entry_annotation(
                str(data.get('sourceType') or data.get('source_type') or ''),
                int(data.get('id') or data.get('source_id') or 0),
                data.get('payload') if isinstance(data.get('payload'), dict) else {},
            )
        )
    if method == 'updateEntrySensitive':
        raw_ids = data.get('ids')
        source_ids = [int(item) for item in raw_ids] if isinstance(raw_ids, list) else None
        return ok(
            service.update_entry_sensitive(
                str(data.get('sourceType') or data.get('source_type') or ''),
                int(data.get('id') or data.get('source_id') or 0),
                bool(data.get('sensitive')),
                str(data.get('reason') or '').strip() or None,
                source_ids,
            )
        )

    handler = handlers.get(method)
    if handler is None:
        raise ApiError(f'Unsupported GUI API method: {method}', 'UNSUPPORTED_GUI_METHOD', 404)

    try:
        return ok(handler(data))
    except ValueError as exc:
        raise ApiError(str(exc), 'INVALID_GUI_REQUEST', 400) from exc
    except Exception as exc:
        raise ApiError(f'GUI API method failed: {method}', 'GUI_METHOD_FAILED', 500) from exc


def _date_arg(data: dict[str, Any]) -> str | None:
    return str(data.get('date') or '').strip() or None
