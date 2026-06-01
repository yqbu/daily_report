from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from daily_report.api.deps import get_overview_service
from daily_report.api.response import ApiError, ok
from daily_report.service.overview_service import OverviewService

router = APIRouter(prefix='/api', tags=['overview'])


@router.get('/overview')
def get_overview(
    date: str | None = Query(default=None),
    service: OverviewService = Depends(get_overview_service),
) -> dict:
    try:
        return ok(service.get_overview(date))
    except Exception as exc:
        raise ApiError('Failed to build overview', 'OVERVIEW_FAILED', 500) from exc

