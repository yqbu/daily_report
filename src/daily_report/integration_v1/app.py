from __future__ import annotations

import asyncio
import re
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from daily_report.integration_v1.projection import (
    IntegrationProjection,
    IntegrationProjectionUnavailable,
    ProjectedReport,
)
from daily_report.integration_v1.revision import canonical_json, stable_etag, stable_revision

SCHEMA_VERSION = 1
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
CAPABILITY_CONTRACT = {
    "schemaVersion": SCHEMA_VERSION,
    "operations": ["daily", "range"],
    "dailyRequired": ["schemaVersion", "meta", "report"],
    "rangeRequired": ["schemaVersion", "meta", "items"],
}
CAPABILITY_REVISION = stable_revision("cap-v1", CAPABILITY_CONTRACT)
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ERROR_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class ProviderError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message = message


def create_integration_app(
    *,
    projection: IntegrationProjection,
    bearer_token: str,
    fault_profile: str = "normal",
) -> FastAPI:
    if not bearer_token:
        raise ValueError("Integration bearer secret is unavailable.")

    app = FastAPI(
        title="daily_report Workbench Integration",
        version="1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )

    @app.exception_handler(ProviderError)
    async def handle_provider_error(_request: Request, exc: ProviderError) -> Response:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, _exc: RequestValidationError) -> Response:
        return _validation_error()

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> Response:
        if exc.status_code == 404:
            return _error_response(404, "not_found", "Resource not found.")
        if exc.status_code == 405:
            return _error_response(405, "method_not_allowed", "Method not allowed.")
        return _error_response(exc.status_code, "request_error", "Request could not be processed.")

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> Response:
        return _error_response(500, "integration_unavailable", "Integration is unavailable.")

    @app.get("/api/integration/v1/capabilities")
    async def capabilities(request: Request) -> Response:
        _verify_bearer(request, bearer_token)
        fault = await _fault_response(request, fault_profile)
        if fault is not None:
            return fault
        schema_version = 2 if fault_profile == "unsupported-schema" else SCHEMA_VERSION
        return _json_response(
            200,
            {
                "ok": True,
                "data": {
                    "schemaVersion": schema_version,
                    "currentRevision": CAPABILITY_REVISION,
                    "operations": ["daily", "range"],
                },
            },
        )

    @app.get("/api/integration/v1/daily/{target_date}")
    async def daily(request: Request, target_date: str) -> Response:
        _verify_bearer(request, bearer_token)
        fault = await _fault_response(request, fault_profile)
        if fault is not None:
            return fault
        parsed_date = _parse_date(target_date)
        _validate_conditional_header(request)
        try:
            projected = projection.get_report(parsed_date.isoformat())
        except IntegrationProjectionUnavailable as exc:
            raise ProviderError(
                503,
                "projection_unavailable",
                "Read-only projection is unavailable.",
            ) from exc
        schema_version = 2 if fault_profile == "unsupported-schema" else SCHEMA_VERSION
        data, revision = _daily_data(
            parsed_date.isoformat(),
            projected,
            generated_at=_resource_generated_at(parsed_date),
            schema_version=schema_version,
        )
        etag = stable_etag(f"daily:{parsed_date.isoformat()}", revision)
        return _conditional_json_response(request, data, etag)

    @app.get("/api/integration/v1/range")
    async def range_summary(request: Request) -> Response:
        _verify_bearer(request, bearer_token)
        fault = await _fault_response(request, fault_profile)
        if fault is not None:
            return fault
        start_date, end_date, limit = _parse_range(request)
        _validate_conditional_header(request)
        try:
            reports = projection.list_reports(
                start_date.isoformat(),
                end_date.isoformat(),
                limit,
            )
        except IntegrationProjectionUnavailable as exc:
            raise ProviderError(
                503,
                "projection_unavailable",
                "Read-only projection is unavailable.",
            ) from exc
        schema_version = 2 if fault_profile == "unsupported-schema" else SCHEMA_VERSION
        data, revision = _range_data(
            start_date.isoformat(),
            end_date.isoformat(),
            limit,
            reports,
            generated_at=_resource_generated_at(end_date),
            schema_version=schema_version,
        )
        resource_key = f"range:{start_date.isoformat()}:{end_date.isoformat()}:{limit}"
        etag = stable_etag(resource_key, revision)
        return _conditional_json_response(request, data, etag)

    return app


def _verify_bearer(request: Request, expected_token: str) -> None:
    value = request.headers.get("authorization")
    if not value:
        raise ProviderError(401, "unauthorized", "Bearer secret is required.")
    scheme, separator, token = value.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token:
        raise ProviderError(401, "unauthorized", "Bearer secret is required.")
    if not secrets.compare_digest(token, expected_token):
        raise ProviderError(403, "forbidden", "Bearer secret was rejected.")


def _parse_date(value: str) -> date:
    if not _DATE_PATTERN.fullmatch(value):
        raise ProviderError(422, "validation_error", "Invalid request parameters.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ProviderError(422, "validation_error", "Invalid request parameters.") from exc
    if parsed.year < 1 or parsed.year > 9999:
        raise ProviderError(422, "validation_error", "Invalid request parameters.")
    return parsed


def _parse_range(request: Request) -> tuple[date, date, int]:
    allowed = {"start", "end", "limit", "afterRevision"}
    values: dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        if key not in allowed:
            raise ProviderError(422, "validation_error", "Invalid request parameters.")
        values.setdefault(key, []).append(value)
    if any(len(items) != 1 for items in values.values()):
        raise ProviderError(422, "validation_error", "Invalid request parameters.")
    if not all(key in values for key in ("start", "end", "limit")):
        raise ProviderError(422, "validation_error", "Invalid request parameters.")

    start = _parse_date(values["start"][0])
    end = _parse_date(values["end"][0])
    limit_text = values["limit"][0]
    if not limit_text.isdigit():
        raise ProviderError(422, "validation_error", "Invalid request parameters.")
    limit = int(limit_text)
    if not 1 <= limit <= 90 or start > end or (end - start).days + 1 > 90:
        raise ProviderError(422, "validation_error", "Invalid request parameters.")

    if "afterRevision" in values:
        revision = values["afterRevision"][0]
        if not 1 <= len(revision) <= 1024:
            raise ProviderError(422, "validation_error", "Invalid request parameters.")
    return start, end, limit


def _validate_conditional_header(request: Request) -> None:
    value = request.headers.get("if-none-match")
    if value is not None and not 1 <= len(value) <= 1024:
        raise ProviderError(422, "validation_error", "Invalid request parameters.")


def _daily_data(
    target_date: str,
    projected: ProjectedReport | None,
    *,
    generated_at: str,
    schema_version: int,
) -> tuple[dict[str, Any], str]:
    report = None
    source_updated_at = None
    if projected is not None:
        _validate_projected_report(projected, expected_date=target_date)
        report = {
            "date": projected.date,
            "reportId": projected.report_id,
            "summary": projected.summary,
        }
        source_updated_at = projected.source_updated_at
    revision_source = {
        "schemaVersion": schema_version,
        "date": target_date,
        "freshness": {"sourceUpdatedAt": source_updated_at},
        "report": report,
    }
    revision = stable_revision("daily-v1", revision_source)
    return (
        {
            "schemaVersion": schema_version,
            "meta": {"revision": revision, "generatedAt": generated_at},
            "freshness": {"sourceUpdatedAt": source_updated_at},
            "report": report,
        },
        revision,
    )


def _range_data(
    start_date: str,
    end_date: str,
    limit: int,
    reports: list[ProjectedReport],
    *,
    generated_at: str,
    schema_version: int,
) -> tuple[dict[str, Any], str]:
    by_date: dict[str, ProjectedReport] = {}
    previous_date: str | None = None
    for projected in reports:
        _validate_projected_report(projected)
        if not start_date <= projected.date <= end_date:
            raise ProviderError(
                500, "invalid_projection", "Read-only projection returned invalid data."
            )
        if previous_date is not None and projected.date <= previous_date:
            raise ProviderError(
                500, "invalid_projection", "Read-only projection returned invalid data."
            )
        previous_date = projected.date
        by_date[projected.date] = projected

    items: list[dict[str, Any]] = []
    current = date.fromisoformat(start_date)
    final = date.fromisoformat(end_date)
    while current <= final and len(items) < limit:
        rendered_date = current.isoformat()
        projected = by_date.get(rendered_date)
        projected_report = None
        if projected is not None:
            projected_report = {
                "reportId": projected.report_id,
                "summary": projected.summary,
            }
        items.append(
            {
                "date": rendered_date,
                "report": projected_report,
            }
        )
        current += timedelta(days=1)
    if len(reports) > limit or len(items) > limit or len(items) > 90:
        raise ProviderError(
            500, "invalid_projection", "Read-only projection returned invalid data."
        )
    revision_source = {
        "schemaVersion": schema_version,
        "start": start_date,
        "end": end_date,
        "limit": limit,
        "items": items,
    }
    revision = stable_revision("range-v1", revision_source)
    return (
        {
            "schemaVersion": schema_version,
            "meta": {"revision": revision, "generatedAt": generated_at},
            "items": items,
        },
        revision,
    )


def _validate_projected_report(
    report: ProjectedReport,
    *,
    expected_date: str | None = None,
) -> None:
    try:
        parsed_date = _parse_date(report.date).isoformat()
    except ProviderError as exc:
        raise ProviderError(
            500, "invalid_projection", "Read-only projection returned invalid data."
        ) from exc
    if expected_date is not None and parsed_date != expected_date:
        raise ProviderError(
            500, "invalid_projection", "Read-only projection returned invalid data."
        )
    if not 1 <= len(report.report_id) <= 256:
        raise ProviderError(
            500, "invalid_projection", "Read-only projection returned invalid data."
        )
    if report.summary is not None and len(report.summary) > 16_384:
        raise ProviderError(
            500, "invalid_projection", "Read-only projection returned invalid data."
        )
    if report.source_updated_at is not None:
        _validate_utc_instant(report.source_updated_at)


def _validate_utc_instant(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProviderError(
            500, "invalid_projection", "Read-only projection returned invalid data."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ProviderError(
            500, "invalid_projection", "Read-only projection returned invalid data."
        )


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _resource_generated_at(value: date) -> str:
    return _format_utc(datetime(value.year, value.month, value.day, tzinfo=UTC))


def _conditional_json_response(request: Request, data: dict[str, Any], etag: str) -> Response:
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return _json_response(200, {"ok": True, "data": data}, headers={"ETag": etag})


def _json_response(
    status_code: int,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
) -> Response:
    content = canonical_json(payload)
    if len(content) > MAX_RESPONSE_BYTES:
        return _error_response(500, "response_too_large", "Integration response is too large.")
    return Response(
        content=content,
        status_code=status_code,
        headers=headers,
        media_type="application/json",
    )


def _error_response(status_code: int, code: str, message: str) -> Response:
    safe_code = code if _ERROR_CODE_PATTERN.fullmatch(code) else "integration_error"
    safe_message = message if 1 <= len(message) <= 512 else "Integration request failed."
    content = canonical_json({"ok": False, "error": {"code": safe_code, "message": safe_message}})
    return Response(content=content, status_code=status_code, media_type="application/json")


def _validation_error() -> Response:
    return _error_response(422, "validation_error", "Invalid request parameters.")


async def _fault_response(request: Request, profile: str) -> Response | None:
    if profile == "normal" or profile == "unsupported-schema":
        return None
    if profile == "redirect":
        return Response(status_code=307, headers={"Location": "/synthetic-redirect-target"})
    if profile == "oversized-response":
        content = b"{" + (b" " * MAX_RESPONSE_BYTES) + b"}"
        return Response(content=content, media_type="application/json")
    if profile == "delayed-response":
        for _ in range(3000):
            if await request.is_disconnected():
                return Response(status_code=499)
            await asyncio.sleep(0.01)
        return _error_response(408, "synthetic_timeout", "Synthetic delayed response.")
    if profile.startswith("status-"):
        try:
            status_code = int(profile.removeprefix("status-"))
        except ValueError:
            status_code = 500
        return _error_response(
            status_code,
            "synthetic_status",
            "Synthetic fault response.",
        )
    raise ProviderError(500, "invalid_profile", "Synthetic profile is invalid.")
