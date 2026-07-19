from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from daily_report.integration_v1.app import create_integration_app
from daily_report.integration_v1.projection import ProjectedReport


TOKEN = "synthetic-read-only-token"


class FakeProjection:
    def __init__(self, reports: list[ProjectedReport] | None = None):
        self.reports = {report.date: report for report in reports or []}

    def get_report(self, target_date: str) -> ProjectedReport | None:
        return self.reports.get(target_date)

    def list_reports(
        self,
        start_date: str,
        end_date: str,
        limit: int,
    ) -> list[ProjectedReport]:
        return [
            report
            for date, report in sorted(self.reports.items())
            if start_date <= date <= end_date
        ][:limit]


def report(
    target_date: str = "2026-07-18",
    *,
    report_id: str = "report-7",
    summary: str | None = "Synthetic summary",
    source_updated_at: str | None = "2026-07-17T23:59:00.000Z",
) -> ProjectedReport:
    return ProjectedReport(
        date=target_date,
        report_id=report_id,
        summary=summary,
        source_updated_at=source_updated_at,
    )


def client_for(
    reports: list[ProjectedReport] | None = None,
    *,
    token: str = TOKEN,
    fault_profile: str = "normal",
) -> TestClient:
    app = create_integration_app(
        projection=FakeProjection(reports),
        bearer_token=token,
        fault_profile=fault_profile,
    )
    return TestClient(app, follow_redirects=False)


def auth(token: str = TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_capabilities_contract_and_stable_revision() -> None:
    client = client_for()

    first = client.get("/api/integration/v1/capabilities", headers=auth())
    second = client.get("/api/integration/v1/capabilities", headers=auth())

    assert first.status_code == 200
    assert first.headers["content-type"].startswith("application/json")
    assert first.json() == second.json()
    assert first.json() == {
        "ok": True,
        "data": {
            "schemaVersion": 1,
            "currentRevision": first.json()["data"]["currentRevision"],
            "operations": ["daily", "range"],
        },
    }
    revision = first.json()["data"]["currentRevision"]
    assert 1 <= len(revision) <= 1024
    assert TOKEN not in revision


@pytest.mark.parametrize(
    ("headers", "status"),
    [({}, 401), (auth("wrong-synthetic-token"), 403)],
)
def test_all_endpoints_require_the_read_only_bearer_secret(
    headers: dict[str, str],
    status: int,
) -> None:
    client = client_for([report()])

    for url in (
        "/api/integration/v1/capabilities",
        "/api/integration/v1/daily/2026-07-18",
        "/api/integration/v1/range?start=2026-07-18&end=2026-07-18&limit=1",
    ):
        response = client.get(url, headers=headers)
        assert response.status_code == status
        assert response.json()["ok"] is False
        assert set(response.json()) == {"ok", "error"}
        assert TOKEN not in response.text


def test_daily_contract_matches_snapshot_and_excludes_private_fields() -> None:
    response = client_for([report()]).get(
        "/api/integration/v1/daily/2026-07-18",
        headers=auth(),
    )

    assert response.status_code == 200
    actual = response.json()
    normalized = copy.deepcopy(actual)
    normalized["data"]["meta"]["revision"] = "<revision>"
    fixture = json.loads(
        Path("tests/fixtures/integration_v1_daily_contract.json").read_text(encoding="utf-8")
    )
    assert normalized == fixture
    serialized = json.dumps(actual)
    for private_name in ("prompt_text", "material_snapshot_json", "report_markdown", "events"):
        assert private_name not in serialized


def test_daily_allows_null_report_and_null_summary() -> None:
    no_report = client_for().get(
        "/api/integration/v1/daily/2026-07-19",
        headers=auth(),
    )
    null_summary = client_for([report(summary=None)]).get(
        "/api/integration/v1/daily/2026-07-18",
        headers=auth(),
    )

    assert no_report.status_code == 200
    assert no_report.json()["data"]["report"] is None
    assert no_report.json()["data"]["freshness"] == {"sourceUpdatedAt": None}
    assert null_summary.status_code == 200
    assert null_summary.json()["data"]["report"]["summary"] is None


def test_range_is_sparse_unique_ascending_and_honors_limit() -> None:
    reports = [
        report("2026-07-18", report_id="report-8"),
        report("2026-07-16", report_id="report-6"),
        report("2026-07-17", report_id="report-7"),
    ]
    response = client_for(reports).get(
        "/api/integration/v1/range?start=2026-07-15&end=2026-07-18&limit=2",
        headers=auth(),
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["schemaVersion"] == 1
    assert [item["date"] for item in payload["items"]] == ["2026-07-15", "2026-07-16"]
    assert all(set(item) == {"date", "report"} for item in payload["items"])
    assert payload["items"][0]["report"] is None
    assert "date" not in payload["items"][1]["report"]


def test_range_after_revision_without_etag_is_a_valid_first_request() -> None:
    response = client_for([report()]).get(
        "/api/integration/v1/range"
        "?start=2026-07-18&end=2026-07-18&limit=1&afterRevision=opaque-checkpoint",
        headers=auth(),
    )

    assert response.status_code == 200
    assert response.headers["etag"]


def test_daily_and_range_conditionals_are_stable_and_resource_isolated() -> None:
    client = client_for([report(), report("2026-07-17", report_id="report-6")])
    daily_url = "/api/integration/v1/daily/2026-07-18"
    other_daily_url = "/api/integration/v1/daily/2026-07-17"
    range_url = "/api/integration/v1/range?start=2026-07-17&end=2026-07-18&limit=2"
    other_range_url = "/api/integration/v1/range?start=2026-07-17&end=2026-07-18&limit=1"

    daily = client.get(daily_url, headers=auth())
    same_daily = client.get(daily_url, headers={**auth(), "If-None-Match": daily.headers["etag"]})
    stale_daily = client.get(daily_url, headers={**auth(), "If-None-Match": '"stale"'})
    other_daily = client.get(other_daily_url, headers=auth())
    range_response = client.get(range_url, headers=auth())
    same_range = client.get(
        range_url,
        headers={**auth(), "If-None-Match": range_response.headers["etag"]},
    )
    other_range = client.get(other_range_url, headers=auth())

    assert daily.status_code == 200
    assert same_daily.status_code == 304
    assert same_daily.content == b""
    assert same_daily.headers["etag"] == daily.headers["etag"]
    assert stale_daily.status_code == 200
    assert other_daily.headers["etag"] != daily.headers["etag"]
    assert range_response.status_code == 200
    assert same_range.status_code == 304
    assert same_range.content == b""
    assert other_range.headers["etag"] != range_response.headers["etag"]


def test_revision_and_etag_change_only_when_public_data_changes() -> None:
    first_client = client_for([report()])
    same_data_new_token = client_for([report()], token="rotated-synthetic-token")
    changed_client = client_for([report(summary="Changed synthetic summary")])
    url = "/api/integration/v1/daily/2026-07-18"

    first = first_client.get(url, headers=auth())
    same = same_data_new_token.get(url, headers=auth("rotated-synthetic-token"))
    changed = changed_client.get(url, headers=auth())

    assert first.headers["etag"] == same.headers["etag"]
    assert first.json()["data"]["meta"]["revision"] == same.json()["data"]["meta"]["revision"]
    assert first.headers["etag"] != changed.headers["etag"]
    assert first.json()["data"]["meta"]["revision"] != changed.json()["data"]["meta"]["revision"]


def test_complete_representation_is_stable_across_app_restarts() -> None:
    first_client = client_for([report()])
    restarted_client = client_for([report()])
    url = "/api/integration/v1/daily/2026-07-18"

    first = first_client.get(url, headers=auth())
    restarted = restarted_client.get(url, headers=auth())

    assert first.headers["etag"] == restarted.headers["etag"]
    assert first.content == restarted.content


@pytest.mark.parametrize(
    "target_date",
    [
        "2025-02-29",
        "2026-13-01",
        "2026-04-31",
        "26-07-18",
        "0000-01-01",
        "10000-01-01",
    ],
)
def test_daily_rejects_non_gregorian_or_non_four_digit_dates(target_date: str) -> None:
    response = client_for().get(
        f"/api/integration/v1/daily/{target_date}",
        headers=auth(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "ok": False,
        "error": {"code": "validation_error", "message": "Invalid request parameters."},
    }


def test_daily_accepts_real_leap_day_and_date_extremes() -> None:
    client = client_for()

    for target_date in ("0001-01-01", "2024-02-29", "9999-12-31"):
        response = client.get(f"/api/integration/v1/daily/{target_date}", headers=auth())
        assert response.status_code == 200


def test_daily_rejects_non_utf8_path_input_safely() -> None:
    response = client_for().get(
        "/api/integration/v1/daily/%FF",
        headers=auth(),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "query",
    [
        "start=2026-07-19&end=2026-07-18&limit=1",
        "start=2026-01-01&end=2026-04-01&limit=90",
        "start=2026-07-18&end=2026-07-18&limit=0",
        "start=2026-07-18&end=2026-07-18&limit=91",
        "start=2026-07-18&end=2026-07-18&limit=1.5",
        "start=2026-07-18&end=2026-07-18&limit=1&limit=2",
        "start=2026-07-18&start=2026-07-17&end=2026-07-18&limit=1",
        "start=2026-07-18&end=2026-07-18",
        "end=2026-07-18&limit=1",
        "start=2026-07-18&limit=1",
        "start=2026-07-18&end=2026-07-18&limit=1&afterRevision=",
    ],
)
def test_range_rejects_invalid_or_duplicate_parameters(query: str) -> None:
    response = client_for().get(f"/api/integration/v1/range?{query}", headers=auth())

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert 1 <= len(error["message"]) <= 512


def test_range_accepts_exactly_ninety_inclusive_days() -> None:
    response = client_for().get(
        "/api/integration/v1/range?start=2026-01-01&end=2026-03-31&limit=90",
        headers=auth(),
    )

    assert response.status_code == 200


def test_oversized_conditional_headers_and_projection_values_are_rejected_safely() -> None:
    client = client_for([report()])
    url = "/api/integration/v1/daily/2026-07-18"

    long_etag = client.get(url, headers={**auth(), "If-None-Match": "x" * 1025})
    long_revision = client.get(
        "/api/integration/v1/range"
        f"?start=2026-07-18&end=2026-07-18&limit=1&afterRevision={'x' * 1025}",
        headers=auth(),
    )
    long_id = client_for([report(report_id="x" * 257)]).get(url, headers=auth())
    long_summary = client_for([report(summary="x" * 16385)]).get(url, headers=auth())

    assert long_etag.status_code == 422
    assert long_revision.status_code == 422
    assert long_id.status_code == 500
    assert long_summary.status_code == 500
    assert "x" * 100 not in long_id.text
    assert "x" * 100 not in long_summary.text


def test_standard_routes_do_not_redirect_or_expose_write_methods() -> None:
    client = client_for()

    trailing_slash = client.get("/api/integration/v1/capabilities/", headers=auth())
    write_attempt = client.post("/api/integration/v1/capabilities", headers=auth())

    assert trailing_slash.status_code == 404
    assert write_attempt.status_code == 405
    assert not 300 <= trailing_slash.status_code < 400
    assert not 300 <= write_attempt.status_code < 400


@pytest.mark.parametrize(
    ("profile", "expected_status"),
    [
        ("status-400", 400),
        ("status-401", 401),
        ("status-403", 403),
        ("status-404", 404),
        ("status-409", 409),
        ("status-422", 422),
        ("status-408", 408),
        ("status-425", 425),
        ("status-429", 429),
        ("status-500", 500),
    ],
)
def test_live_fault_status_profiles_use_safe_envelopes(
    profile: str,
    expected_status: int,
) -> None:
    response = client_for(fault_profile=profile).get(
        "/api/integration/v1/capabilities",
        headers=auth(),
    )

    assert response.status_code == expected_status
    assert response.json()["ok"] is False
    assert set(response.json()["error"]) == {"code", "message"}


def test_unsupported_schema_and_redirect_fault_profiles_are_detectable() -> None:
    unsupported = client_for(fault_profile="unsupported-schema").get(
        "/api/integration/v1/capabilities",
        headers=auth(),
    )
    redirect = client_for(fault_profile="redirect").get(
        "/api/integration/v1/capabilities",
        headers=auth(),
    )

    assert unsupported.status_code == 200
    assert unsupported.json()["data"]["schemaVersion"] == 2
    assert redirect.status_code == 307


def test_main_api_openapi_is_unchanged_and_provider_openapi_is_read_only() -> None:
    from daily_report.api.app import create_app

    main_paths = create_app().openapi()["paths"]
    provider_paths = client_for().app.openapi()["paths"]

    assert not any(path.startswith("/api/integration/") for path in main_paths)
    assert set(provider_paths) == {
        "/api/integration/v1/capabilities",
        "/api/integration/v1/daily/{target_date}",
        "/api/integration/v1/range",
    }
    assert all(set(operations) == {"get"} for operations in provider_paths.values())
