from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from daily_report.api.deps import verify_token
from daily_report.api.response import ApiError, error_response
from daily_report.api.routes import browser_events, desktop, entries, health, overview, reports, runtime, settings, timeline

logger = logging.getLogger(__name__)


def create_app(api_token: str | None = None) -> FastAPI:
    app = FastAPI(title='Daily Report API', version=_package_version())
    app.state.api_token = api_token or ''

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r'^(http://(localhost|127\.0\.0\.1)(:\d+)?|tauri://localhost)$',
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'X-Daily-Report-Token'],
    )

    app.include_router(health.router)
    app.include_router(browser_events.public_router)
    protected = [
        overview.router,
        timeline.router,
        entries.router,
        reports.router,
        runtime.router,
        settings.router,
        desktop.router,
        browser_events.protected_router,
    ]
    for router in protected:
        app.include_router(router, dependencies=[Depends(verify_token)])

    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError):
        return error_response(exc.error, exc.code, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError):
        logger.debug('API request validation failed: %s', exc)
        return error_response('Invalid request parameters', 'VALIDATION_ERROR', 422)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception):
        logger.exception('Unhandled API error.')
        return error_response('Internal server error', 'INTERNAL_ERROR', 500)

    return app


def _package_version() -> str:
    try:
        return version('daily-report')
    except PackageNotFoundError:
        return '0.1.0'

