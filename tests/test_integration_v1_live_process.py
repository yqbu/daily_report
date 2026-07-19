from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil
import pytest

from daily_report.integration_v1.app import MAX_RESPONSE_BYTES
from daily_report.integration_v1.server import (
    CAPABILITY_REVISION,
    FIXTURE_ID,
    READINESS_FILE_NAME,
    TOKEN_FILE_NAME,
)


@dataclass
class LiveProvider:
    process: subprocess.Popen[str]
    runtime_dir: Path
    base_url: str
    token: str
    readiness: dict[str, Any]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def start_provider(runtime_dir: Path, profile: str = "normal") -> LiveProvider:
    runtime_dir.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable,
        "-m",
        "daily_report.main",
        "integration",
        "live-test",
        "--test-only",
        "--runtime-dir",
        str(runtime_dir),
        "--profile",
        profile,
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.environ.get(
        "DAILY_REPORT_LIVE_PYTHONPATH",
        str(Path.cwd() / "src"),
    )
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=Path.cwd(),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        creationflags=creation_flags,
    )

    readiness_path = runtime_dir / READINESS_FILE_NAME
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"provider exited before readiness: code={process.returncode}, "
                f"stdout_length={len(stdout)}, stderr_length={len(stderr)}"
            )
        if readiness_path.exists():
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            token = (runtime_dir / TOKEN_FILE_NAME).read_text(encoding="utf-8")
            return LiveProvider(
                process=process,
                runtime_dir=runtime_dir,
                base_url=readiness["baseUrl"],
                token=token,
                readiness=readiness,
            )
        time.sleep(0.01)
    stop_provider_process(process)
    raise AssertionError("provider readiness deadline exceeded")


def stop_provider_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    if process.poll() is None:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.communicate(timeout=2)


def request(
    provider: LiveProvider,
    path: str,
    *,
    token: str | None = None,
    etag: str | None = None,
    timeout: float = 5,
    max_bytes: int | None = None,
    follow_redirects: bool = False,
) -> tuple[int, dict[str, str], bytes]:
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if etag is not None:
        headers["If-None-Match"] = etag
    outgoing = urllib.request.Request(provider.base_url + path, headers=headers, method="GET")
    opener = (
        urllib.request.build_opener()
        if follow_redirects
        else urllib.request.build_opener(NoRedirect)
    )
    try:
        with opener.open(outgoing, timeout=timeout) as response:
            body = response.read(max_bytes) if max_bytes is not None else response.read()
            return (
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                body,
            )
    except urllib.error.HTTPError as error:
        body = error.read(max_bytes) if max_bytes is not None else error.read()
        return error.code, {key.lower(): value for key, value in error.headers.items()}, body


def wait_until_removed(path: Path) -> None:
    deadline = time.monotonic() + 2
    while path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not path.exists()


def test_normal_live_process_contract_conditionals_loopback_and_cleanup(tmp_path: Path) -> None:
    provider = start_provider(tmp_path / "normal")
    port = int(provider.base_url.rsplit(":", 1)[1])
    try:
        assert isinstance(provider.readiness["pid"], int)
        assert provider.readiness["pid"] > 0
        assert provider.readiness == {
            "pid": provider.readiness["pid"],
            "baseUrl": provider.base_url,
            "fixtureId": FIXTURE_ID,
            "capabilityRevision": CAPABILITY_REVISION,
            "secretReference": "daily-report.integration.v1.live-token",
        }

        capability_status, _, capability_body = request(
            provider,
            "/api/integration/v1/capabilities",
            token=provider.token,
        )
        capability = json.loads(capability_body)
        assert capability_status == 200
        assert capability["data"]["schemaVersion"] == 1
        assert capability["data"]["operations"] == ["daily", "range"]

        daily_status, daily_headers, daily_body = request(
            provider,
            "/api/integration/v1/daily/2026-07-18",
            token=provider.token,
        )
        null_status, _, null_body = request(
            provider,
            "/api/integration/v1/daily/2026-07-19",
            token=provider.token,
        )
        assert daily_status == 200
        assert len(daily_body) < MAX_RESPONSE_BYTES
        assert daily_headers["etag"]
        assert json.loads(daily_body)["data"]["report"] is not None
        assert null_status == 200
        assert json.loads(null_body)["data"]["report"] is None

        cached_status, cached_headers, cached_body = request(
            provider,
            "/api/integration/v1/daily/2026-07-18",
            token=provider.token,
            etag=daily_headers["etag"],
        )
        assert cached_status == 304
        assert cached_body == b""
        assert cached_headers["etag"] == daily_headers["etag"]

        range_path = "/api/integration/v1/range?start=2026-07-14&end=2026-07-18&limit=5"
        range_status, range_headers, range_body = request(
            provider,
            range_path,
            token=provider.token,
        )
        range_data = json.loads(range_body)["data"]
        assert range_status == 200
        assert [item["date"] for item in range_data["items"]] == sorted(
            item["date"] for item in range_data["items"]
        )
        assert any(item["report"] is None for item in range_data["items"])
        range_cached, _, range_cached_body = request(
            provider,
            range_path,
            token=provider.token,
            etag=range_headers["etag"],
        )
        assert range_cached == 304
        assert range_cached_body == b""
        assert range_headers["etag"] != daily_headers["etag"]

        missing_status, _, missing_body = request(
            provider,
            "/api/integration/v1/capabilities",
        )
        wrong_status, _, wrong_body = request(
            provider,
            "/api/integration/v1/capabilities",
            token="wrong-synthetic-token",
        )
        assert missing_status == 401
        assert wrong_status == 403
        assert provider.token.encode() not in missing_body + wrong_body

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    request,
                    provider,
                    "/api/integration/v1/daily/2026-07-18",
                    token=provider.token,
                )
                for _ in range(2)
            ]
        assert [future.result()[0] for future in futures] == [200, 200]

        listeners = [
            connection
            for connection in psutil.net_connections(kind="tcp")
            if connection.pid == provider.readiness["pid"]
            and connection.status == psutil.CONN_LISTEN
            and connection.laddr.port == port
        ]
        assert listeners
        assert {connection.laddr.ip for connection in listeners} == {"127.0.0.1"}
        non_loopback_addresses = {
            address.address
            for addresses in psutil.net_if_addrs().values()
            for address in addresses
            if address.family == socket.AF_INET and not address.address.startswith("127.")
        }
        for address in non_loopback_addresses:
            with pytest.raises(OSError):
                socket.create_connection((address, port), timeout=0.2)
    finally:
        stdout, stderr = stop_provider_process(provider.process)

    assert provider.token not in stdout
    assert provider.token not in stderr
    wait_until_removed(provider.runtime_dir)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as released:
        released.bind(("127.0.0.1", port))


def test_restart_rotates_secret_but_preserves_fixture_etag(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "restart"
    first = start_provider(runtime_dir)
    first_status, first_headers, _ = request(
        first,
        "/api/integration/v1/daily/2026-07-18",
        token=first.token,
    )
    stop_provider_process(first.process)
    wait_until_removed(runtime_dir)

    second = start_provider(runtime_dir)
    try:
        old_status, _, _ = request(
            second,
            "/api/integration/v1/daily/2026-07-18",
            token=first.token,
        )
        new_status, second_headers, _ = request(
            second,
            "/api/integration/v1/daily/2026-07-18",
            token=second.token,
        )
        assert first_status == 200
        assert old_status == 403
        assert new_status == 200
        assert first.token != second.token
        assert first_headers["etag"] == second_headers["etag"]
    finally:
        stop_provider_process(second.process)
    wait_until_removed(runtime_dir)


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
def test_status_fault_profiles_use_real_processes(
    tmp_path: Path,
    profile: str,
    expected_status: int,
) -> None:
    provider = start_provider(tmp_path / profile, profile)
    try:
        status, _, body = request(
            provider,
            "/api/integration/v1/capabilities",
            token=provider.token,
        )
        assert status == expected_status
        assert json.loads(body)["ok"] is False
    finally:
        stop_provider_process(provider.process)
    wait_until_removed(provider.runtime_dir)


def test_schema_redirect_oversize_and_delay_faults_use_real_processes(tmp_path: Path) -> None:
    unsupported = start_provider(tmp_path / "schema", "unsupported-schema")
    try:
        status, _, body = request(
            unsupported,
            "/api/integration/v1/capabilities",
            token=unsupported.token,
        )
        assert status == 200
        assert json.loads(body)["data"]["schemaVersion"] == 2
    finally:
        stop_provider_process(unsupported.process)
    wait_until_removed(unsupported.runtime_dir)

    redirect = start_provider(tmp_path / "redirect", "redirect")
    try:
        status, _, _ = request(
            redirect,
            "/api/integration/v1/capabilities",
            token=redirect.token,
        )
        assert status == 307
    finally:
        stop_provider_process(redirect.process)
    wait_until_removed(redirect.runtime_dir)

    oversized = start_provider(tmp_path / "oversized", "oversized-response")
    try:
        status, _, body = request(
            oversized,
            "/api/integration/v1/capabilities",
            token=oversized.token,
            max_bytes=MAX_RESPONSE_BYTES + 1,
        )
        assert status == 200
        assert len(body) > MAX_RESPONSE_BYTES
    finally:
        stop_provider_process(oversized.process)
    wait_until_removed(oversized.runtime_dir)

    delayed = start_provider(tmp_path / "delayed", "delayed-response")
    started = time.monotonic()
    try:
        with pytest.raises((TimeoutError, urllib.error.URLError)):
            request(
                delayed,
                "/api/integration/v1/capabilities",
                token=delayed.token,
                timeout=0.2,
            )
        assert time.monotonic() - started < 5
    finally:
        stop_provider_process(delayed.process)
    wait_until_removed(delayed.runtime_dir)
