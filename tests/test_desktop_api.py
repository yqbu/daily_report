from __future__ import annotations

from fastapi.testclient import TestClient

from daily_report.api.app import create_app


def test_desktop_api_exposes_overview(tmp_path, monkeypatch):
    monkeypatch.setenv('DAILY_REPORT_DATA_DIR', str(tmp_path))
    client = TestClient(create_app())

    response = client.post('/api/desktop/getOverview', json={'date': '2026-07-12'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['data']['date'] == '2026-07-12'


def test_desktop_api_rejects_unknown_method(tmp_path, monkeypatch):
    monkeypatch.setenv('DAILY_REPORT_DATA_DIR', str(tmp_path))
    client = TestClient(create_app())

    response = client.post('/api/desktop/unknownMethod', json={})

    assert response.status_code == 404
    assert response.json()['code'] == 'UNSUPPORTED_DESKTOP_METHOD'
