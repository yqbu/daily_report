from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import tempfile
from pathlib import Path
from typing import Any

import uvicorn

from daily_report.integration_v1.app import CAPABILITY_REVISION, create_integration_app
from daily_report.integration_v1.fixtures import (
    FIXTURE_ID,
    SyntheticIntegrationProjection,
)
from daily_report.integration_v1.projection import IntegrationProjectionService
from daily_report.storage.read_models.integration_report_reader import (
    ReadonlyIntegrationReportReader,
)

SECRET_REFERENCE = "daily-report.integration.v1.live-token"
TOKEN_FILE_NAME = "integration-token"
READINESS_FILE_NAME = "readiness.json"
_ALLOWED_PROFILES = {
    "normal",
    "unsupported-schema",
    "redirect",
    "oversized-response",
    "delayed-response",
    "status-400",
    "status-401",
    "status-403",
    "status-404",
    "status-409",
    "status-422",
    "status-408",
    "status-425",
    "status-429",
    "status-500",
}


def validate_loopback_host(host: str) -> str:
    if host not in {"127.0.0.1", "::1"}:
        raise ValueError("Integration provider requires an explicit loopback address.")
    return host


def validate_runtime_directory(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(temp_root)
    except ValueError as exc:
        raise ValueError(
            "Live-test runtime directory must be inside the OS temporary directory."
        ) from exc
    if resolved == temp_root:
        raise ValueError(
            "Live-test runtime directory must be a child of the OS temporary directory."
        )
    return resolved


def run_production_provider(
    *,
    host: str,
    port: int,
    bearer_token: str,
    db_path: str | Path | None,
) -> None:
    validate_loopback_host(host)
    _validate_port(port)
    if not bearer_token:
        raise ValueError("Integration bearer secret is unavailable.")
    if db_path is None:
        from daily_report.storage.database import default_db_path

        resolved_db_path = default_db_path()
    else:
        resolved_db_path = Path(db_path)
    projection = IntegrationProjectionService(ReadonlyIntegrationReportReader(resolved_db_path))
    app = create_integration_app(
        projection=projection,
        bearer_token=bearer_token,
    )
    listening_socket = _bind_socket(host, port)
    resolved_port = int(listening_socket.getsockname()[1])
    readiness = {
        "baseUrl": _base_url(host, resolved_port),
        "capabilityRevision": CAPABILITY_REVISION,
        "status": "available",
    }
    print(json.dumps(readiness, ensure_ascii=False, separators=(",", ":")), flush=True)
    _run_uvicorn(app, listening_socket)


def run_live_test_provider(
    *,
    host: str,
    port: int,
    runtime_dir: str | Path,
    profile: str,
) -> None:
    validate_loopback_host(host)
    _validate_port(port)
    if profile not in _ALLOWED_PROFILES:
        raise ValueError("Unknown synthetic fault profile.")

    directory = validate_runtime_directory(runtime_dir)
    directory.mkdir(parents=True, exist_ok=True)
    token_path = directory / TOKEN_FILE_NAME
    readiness_path = directory / READINESS_FILE_NAME
    bearer_token = secrets.token_urlsafe(48)
    listening_socket: socket.socket | None = None
    token_created = False
    readiness_created = False
    try:
        _write_private_file(token_path, bearer_token.encode("utf-8"))
        token_created = True
        app = create_integration_app(
            projection=SyntheticIntegrationProjection(),
            bearer_token=bearer_token,
            fault_profile=profile,
        )
        listening_socket = _bind_socket(host, port)
        resolved_port = int(listening_socket.getsockname()[1])
        readiness = {
            "pid": os.getpid(),
            "baseUrl": _base_url(host, resolved_port),
            "fixtureId": FIXTURE_ID,
            "capabilityRevision": CAPABILITY_REVISION,
            "secretReference": SECRET_REFERENCE,
        }
        _write_private_file(
            readiness_path,
            json.dumps(readiness, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        )
        readiness_created = True
        print(json.dumps(readiness, ensure_ascii=False, separators=(",", ":")), flush=True)
        _run_uvicorn(app, listening_socket)
    finally:
        if listening_socket is not None:
            listening_socket.close()
        if readiness_created:
            _remove_file(readiness_path)
        if token_created:
            _remove_file(token_path)
        try:
            directory.rmdir()
        except OSError:
            pass


def _bind_socket(host: str, port: int) -> socket.socket:
    family = socket.AF_INET6 if host == "::1" else socket.AF_INET
    listening_socket = socket.socket(family, socket.SOCK_STREAM)
    try:
        listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listening_socket.bind((host, port))
        listening_socket.listen(128)
        listening_socket.set_inheritable(False)
        return listening_socket
    except Exception:
        listening_socket.close()
        raise


def _run_uvicorn(app: Any, listening_socket: socket.socket) -> None:
    configuration = uvicorn.Config(
        app,
        log_level="critical",
        access_log=False,
        lifespan="on",
    )
    server = uvicorn.Server(configuration)
    previous_sigbreak: Any = None
    if os.name == "nt" and hasattr(signal, "SIGBREAK"):
        previous_sigbreak = signal.signal(
            signal.SIGBREAK,
            lambda _signum, _frame: setattr(server, "should_exit", True),
        )
    try:
        server.run(sockets=[listening_socket])
    finally:
        if previous_sigbreak is not None:
            signal.signal(signal.SIGBREAK, previous_sigbreak)


def _write_private_file(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, content)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _base_url(host: str, port: int) -> str:
    rendered_host = f"[{host}]" if ":" in host else host
    return f"http://{rendered_host}:{port}"


def _validate_port(port: int) -> None:
    if not 0 <= int(port) <= 65535:
        raise ValueError("Integration provider port is invalid.")
