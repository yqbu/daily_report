from __future__ import annotations

import argparse
import ast
import logging
import socket
import subprocess
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from daily_report.integration_v1.app import create_integration_app
from daily_report.main import run_integration_serve


class ExplodingProjection:
    @staticmethod
    def get_report(_target_date: str):
        raise RuntimeError("private path and secret-like internal exception")

    @staticmethod
    def list_reports(_start_date: str, _end_date: str, _limit: int):
        raise RuntimeError("private path and secret-like internal exception")


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_http_adapter_depends_only_on_public_projection_boundary() -> None:
    modules = imported_modules(Path("src/daily_report/integration_v1/app.py"))

    assert not any(module.startswith("daily_report.storage") for module in modules)
    assert not any(module.startswith("daily_report.service") for module in modules)
    assert not any(module.startswith("daily_report.reporter") for module in modules)


def test_readonly_boundary_contains_no_mutating_sql_or_generation_imports() -> None:
    reader = Path("src/daily_report/storage/read_models/integration_report_reader.py").read_text(
        encoding="utf-8"
    )
    projection_modules = imported_modules(Path("src/daily_report/integration_v1/projection.py"))

    normalized_reader = " ".join(reader.upper().split())
    for statement in ("INSERT INTO", "UPDATE ", "DELETE FROM", "ALTER TABLE", "CREATE TABLE"):
        assert statement not in normalized_reader
    assert "MODE=RO" in normalized_reader
    assert "PRAGMA QUERY_ONLY" in normalized_reader
    assert not any(module.startswith("daily_report.reporter") for module in projection_modules)
    assert not any(module.startswith("daily_report.service") for module in projection_modules)


def test_disabled_provider_creates_no_runtime_resources_or_logs(monkeypatch, caplog) -> None:
    calls: list[str] = []

    def fail_socket(*_args, **_kwargs):
        calls.append("socket")
        raise AssertionError("disabled mode created a socket")

    def fail_thread(*_args, **_kwargs):
        calls.append("thread")
        raise AssertionError("disabled mode created a thread")

    def fail_process(*_args, **_kwargs):
        calls.append("process")
        raise AssertionError("disabled mode created a process")

    monkeypatch.setattr(socket, "socket", fail_socket)
    monkeypatch.setattr(threading, "Thread", fail_thread)
    monkeypatch.setattr(subprocess, "Popen", fail_process)
    caplog.set_level(logging.DEBUG)

    run_integration_serve(argparse.Namespace(enabled=None))
    run_integration_serve(argparse.Namespace(enabled=False))

    assert calls == []
    assert caplog.records == []


def test_unexpected_projection_failure_returns_only_generic_error() -> None:
    app = create_integration_app(
        projection=ExplodingProjection(),
        bearer_token="synthetic-secret",
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/api/integration/v1/daily/2026-07-18",
        headers={"Authorization": "Bearer synthetic-secret"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error": {
            "code": "integration_unavailable",
            "message": "Integration is unavailable.",
        },
    }
    assert "private path" not in response.text


def test_integration_documentation_states_public_ownership_and_versioning_rules() -> None:
    documentation = Path("docs/integration-api-v1.md").read_text(encoding="utf-8")

    for required in (
        "/api/integration/v1/capabilities",
        "/api/integration/v1/daily/{YYYY-MM-DD}",
        "/api/integration/v1/range",
        "Bearer Secret",
        "Revision 与 HTTP Cache",
        "数据所有权与只读边界",
        "Desktop RPC",
        "Schema Version 升级规则",
        "默认关闭",
    ):
        assert required in documentation
