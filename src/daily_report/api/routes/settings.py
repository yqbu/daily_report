from __future__ import annotations

from fastapi import APIRouter, Depends

from daily_report.api.deps import get_settings_service
from daily_report.api.response import ApiError, ok
from daily_report.api.schemas import SettingsUpdateRequest
from daily_report.service.settings_service import SettingsService

router = APIRouter(prefix='/api/settings', tags=['settings'])


@router.get('')
def get_settings(service: SettingsService = Depends(get_settings_service)) -> dict:
    try:
        return ok(service.get_settings())
    except Exception as exc:
        raise ApiError('Failed to read settings', 'SETTINGS_READ_FAILED', 500) from exc


@router.put('')
def save_settings(
    payload: SettingsUpdateRequest,
    service: SettingsService = Depends(get_settings_service),
) -> dict:
    try:
        data = payload.dict(exclude_none=True)
        return ok(service.save_settings(data))
    except Exception as exc:
        raise ApiError('Failed to save settings', 'SETTINGS_SAVE_FAILED', 500) from exc

