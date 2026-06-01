from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter, Depends

from daily_report.api.deps import get_overview_service
from daily_report.api.response import ok
from daily_report.service.overview_service import OverviewService

router = APIRouter(prefix='/api', tags=['health'])


@router.get('/health')
def get_health() -> dict:
    return ok(
        {
            'status': 'ok',
            'service': 'daily-report-api',
            'version': _package_version(),
        }
    )


@router.get('/health/collectors')
def get_collector_health(service: OverviewService = Depends(get_overview_service)) -> dict:
    try:
        overview = service.get_overview()
    except Exception:
        return ok(
            {
                'collectors': [],
                'message': 'collector health service is not fully implemented yet',
            }
        )
    return ok(
        {
            'collector_status': overview.get('collector_status', 'unknown'),
            'collector_status_label': overview.get('collector_status_label', 'unknown'),
            'collector_states': overview.get('collector_states', []),
        }
    )


def _package_version() -> str:
    try:
        return version('daily-report')
    except PackageNotFoundError:
        return '0.1.0'

