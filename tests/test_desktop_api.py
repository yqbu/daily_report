from __future__ import annotations

from fastapi.testclient import TestClient

from daily_report.api.app import create_app
from daily_report.api.deps import get_runtime_process_service
from daily_report.service.runtime_process_service import RuntimeProcessInfo


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


def test_runtime_processes_endpoint_uses_full_scan_only_when_requested(tmp_path, monkeypatch):
    monkeypatch.setenv('DAILY_REPORT_DATA_DIR', str(tmp_path))
    calls: list[str] = []
    process = RuntimeProcessInfo(
        pid=123,
        parent_pid=None,
        role='api',
        process_name='python.exe',
        exe_path=None,
        cmdline=['python', '-m', 'daily_report.main', 'api'],
        cmdline_preview='python -m daily_report.main api',
        cwd=None,
        username=None,
        started_at=None,
        cpu_percent=None,
        memory_mb=None,
        port=8765,
        status='running',
        is_current_project=True,
        is_registered=True,
        is_orphan=False,
        is_duplicate=False,
        risk_level='safe',
        reason=None,
    )

    class FakeRuntimeService:
        @staticmethod
        def list_registered_processes():
            calls.append('quick')
            return [process]

        @staticmethod
        def list_processes():
            calls.append('full')
            return [process]

    app = create_app()
    app.dependency_overrides[get_runtime_process_service] = FakeRuntimeService
    client = TestClient(app)

    quick_response = client.get('/api/runtime/processes')
    full_response = client.get('/api/runtime/processes?full=true')

    assert quick_response.status_code == 200
    assert full_response.status_code == 200
    assert calls == ['quick', 'full']
