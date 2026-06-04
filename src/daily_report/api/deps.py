from __future__ import annotations

from typing import Annotated

from fastapi import Header, Request

from daily_report.api.response import ApiError
from daily_report.service.browser_event_service import BrowserEventService
from daily_report.service.overview_service import OverviewService
from daily_report.service.report_service import ReportService
from daily_report.service.settings_service import SettingsService
from daily_report.service.timeline_service import TimelineService


def get_overview_service() -> OverviewService:
    return OverviewService()


def get_timeline_service() -> TimelineService:
    return TimelineService()


def get_report_service() -> ReportService:
    return ReportService()


def get_settings_service() -> SettingsService:
    return SettingsService()


def get_browser_event_service() -> BrowserEventService:
    return BrowserEventService()


async def verify_token(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_daily_report_token: Annotated[str | None, Header()] = None,
) -> None:
    token = str(getattr(request.app.state, 'api_token', '') or '').strip()
    if not token:
        return
    if authorization == f'Bearer {token}' or x_daily_report_token == token:
        return
    if authorization != f'Bearer {token}':
        raise ApiError('Unauthorized', 'UNAUTHORIZED', status_code=401)

