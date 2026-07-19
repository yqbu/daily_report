from __future__ import annotations

import argparse
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from daily_report.api.app import create_app
from daily_report.integration_v1.server import (
    TOKEN_FILE_NAME,
    run_live_test_provider,
    validate_loopback_host,
    validate_runtime_directory,
)
from daily_report.main import run_integration_serve


@pytest.mark.parametrize("host", ["127.0.0.1", "::1"])
def test_server_accepts_only_explicit_loopback_addresses(host: str) -> None:
    assert validate_loopback_host(host) == host


@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "::", "localhost", "192.168.1.7", "10.0.0.8", "example.test"],
)
def test_server_rejects_wildcard_names_and_non_loopback_addresses(host: str) -> None:
    with pytest.raises(ValueError, match="loopback"):
        validate_loopback_host(host)


def test_live_runtime_directory_must_be_inside_os_temp(tmp_path: Path) -> None:
    accepted = tmp_path / "integration-runtime"
    assert validate_runtime_directory(accepted) == accepted.resolve()

    with pytest.raises(ValueError, match="temporary"):
        validate_runtime_directory(Path.cwd() / "integration-runtime")


def test_secret_failure_isolated_from_existing_health_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("SYNTHETIC_MISSING_SECRET", raising=False)
    args = argparse.Namespace(
        enabled=True,
        secret_env="SYNTHETIC_MISSING_SECRET",
        host="127.0.0.1",
        port=0,
        db_path=None,
    )

    with pytest.raises(SystemExit) as error:
        run_integration_serve(args)

    assert error.value.code == 1
    assert "secret_unavailable" in capsys.readouterr().err
    assert TestClient(create_app()).get("/api/health").status_code == 200


def test_occupied_provider_port_does_not_damage_existing_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    monkeypatch.setenv("SYNTHETIC_PROVIDER_SECRET", "synthetic-secret")
    args = argparse.Namespace(
        enabled=True,
        secret_env="SYNTHETIC_PROVIDER_SECRET",
        host="127.0.0.1",
        port=port,
        db_path="synthetic-missing.db",
    )
    try:
        with pytest.raises(SystemExit) as error:
            run_integration_serve(args)
    finally:
        listener.close()

    assert error.value.code == 1
    assert TestClient(create_app()).get("/api/health").json()["ok"] is True


def test_unexpected_provider_startup_failure_is_redacted_and_isolated(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_startup(**_kwargs) -> None:
        raise RuntimeError("private startup details")

    monkeypatch.setenv("SYNTHETIC_PROVIDER_SECRET", "synthetic-secret")
    monkeypatch.setattr(
        "daily_report.integration_v1.server.run_production_provider",
        fail_startup,
    )
    args = argparse.Namespace(
        enabled=True,
        secret_env="SYNTHETIC_PROVIDER_SECRET",
        host="127.0.0.1",
        port=0,
        db_path="synthetic-missing.db",
    )

    with pytest.raises(SystemExit) as error:
        run_integration_serve(args)

    assert error.value.code == 1
    assert capsys.readouterr().err == "Integration V1 unavailable: startup_failed\n"
    assert TestClient(create_app()).get("/api/health").status_code == 200


def test_live_test_bind_failure_removes_temporary_secret_files(tmp_path: Path) -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    runtime_dir = tmp_path / "bind-failure"
    try:
        with pytest.raises(OSError):
            run_live_test_provider(
                host="127.0.0.1",
                port=listener.getsockname()[1],
                runtime_dir=runtime_dir,
                profile="normal",
            )
    finally:
        listener.close()

    assert not runtime_dir.exists()


def test_live_test_never_deletes_a_preexisting_unowned_secret_file(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "preexisting"
    runtime_dir.mkdir()
    existing_secret = runtime_dir / TOKEN_FILE_NAME
    existing_secret.write_text("preexisting-synthetic-content", encoding="utf-8")

    with pytest.raises(FileExistsError):
        run_live_test_provider(
            host="127.0.0.1",
            port=0,
            runtime_dir=runtime_dir,
            profile="normal",
        )

    assert existing_secret.read_text(encoding="utf-8") == "preexisting-synthetic-content"
    assert runtime_dir.exists()
