from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from daily_report.service.runtime_process_service import RuntimeProcessInfo, RuntimeProcessService
from daily_report.service.single_instance import SingleInstanceError
from daily_report.storage.database import create_connection, init_database
from daily_report.storage.repositories.collector_state_repository import CollectorStateRepository
from daily_report.storage.repositories.runtime_process_repository import RuntimeProcessRepository


def make_service(tmp_path) -> RuntimeProcessService:
    project_root = tmp_path / "daily_report"
    project_root.mkdir()
    return RuntimeProcessService(db_path=tmp_path / "daily_report.db", project_root=project_root)


def make_process(
    service: RuntimeProcessService,
    *,
    pid: int,
    parent_pid: int | None,
    role: str,
    cmdline: list[str],
    port: int | None = None,
    started_at: str = "2026-07-12T10:00:00",
    is_registered: bool = False,
) -> RuntimeProcessInfo:
    return RuntimeProcessInfo(
        pid=pid,
        parent_pid=parent_pid,
        role=role,
        process_name="python.exe" if role in {"api", "collector"} else "node.exe",
        exe_path=None,
        cmdline=cmdline,
        cmdline_preview=" ".join(cmdline),
        cwd=str(service.project_root),
        username=None,
        started_at=started_at,
        cpu_percent=0.0,
        memory_mb=10.0,
        port=port,
        status="running",
        is_current_project=True,
        is_registered=is_registered,
        is_orphan=False,
        is_duplicate=False,
        risk_level="safe",
        reason=None,
    )


def test_runtime_role_identification(tmp_path):
    service = make_service(tmp_path)

    assert service.identify_role(
        cmdline=["python", "-m", "daily_report.main", "run"],
        cwd=str(service.project_root),
        process_name="python.exe",
    ) == "collector"
    assert service.identify_role(
        cmdline=["python", "-m", "daily_report.main", "api"],
        cwd=str(service.project_root),
        process_name="python.exe",
    ) == "api"
    assert service.identify_role(
        cmdline=["npm.cmd", "run", "tauri", "dev"],
        cwd=str(service.project_root),
        process_name="npm.cmd",
    ) == "tauri"
    assert service.identify_role(
        cmdline=["python", "-m", "daily_report.main", "runtime", "status"],
        cwd=str(service.project_root),
        process_name="python.exe",
    ) == "runtime_cli"


def test_current_project_rules_do_not_match_unrelated_python(tmp_path):
    service = make_service(tmp_path)

    is_current, reason = service.is_current_project_process(
        cmdline=["python.exe", "other_tool.py"],
        cwd=str(tmp_path / "other"),
        exe_path="C:/Python/python.exe",
    )

    assert not is_current
    assert reason is None


def test_unknown_process_is_not_safe_to_manage(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    process = RuntimeProcessInfo(
        pid=123456,
        parent_pid=1,
        role="unknown_daily_report",
        process_name="git.exe",
        exe_path=None,
        cmdline=["git", "status"],
        cmdline_preview="git status",
        cwd=str(service.project_root),
        username=None,
        started_at=None,
        cpu_percent=None,
        memory_mb=None,
        port=None,
        status="running",
        is_current_project=True,
        is_registered=False,
        is_orphan=False,
        is_duplicate=False,
        risk_level="safe",
        reason="cwd is inside current project",
    )
    monkeypatch.setattr(service, "list_processes", lambda: [process])

    try:
        service.terminate_process(process.pid)
    except RuntimeError as exc:
        assert "not safe to manage" in str(exc)
    else:
        raise AssertionError("unknown process should not be manageable")


def test_runtime_process_repository_cleanup_stale_records(tmp_path):
    db_path = tmp_path / "daily_report.db"
    conn = create_connection(db_path)
    try:
        init_database(conn)
        repo = RuntimeProcessRepository(conn)
        repo.register_process(role="collector", pid=999999, status="running")

        assert repo.cleanup_stale_records(set()) == 1
        rows = repo.list_by_role("collector")
    finally:
        conn.close()

    assert rows[0]["status"] == "exited"


def test_duplicate_detection_counts_only_extra_business_instances(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    first_api = ["python", "-m", "daily_report.main", "api", "--port", "8012"]
    second_api = ["python", "-m", "daily_report.main", "api", "--port", "8574"]
    processes = [
        make_process(service, pid=100, parent_pid=1, role="api", cmdline=first_api),
        make_process(service, pid=101, parent_pid=100, role="api", cmdline=["python", "api-worker"], port=8012, is_registered=True),
        make_process(service, pid=200, parent_pid=1, role="api", cmdline=second_api, started_at="2026-07-12T11:00:00"),
        make_process(service, pid=201, parent_pid=200, role="api", cmdline=["python", "api-worker"], port=8574, started_at="2026-07-12T11:00:00", is_registered=True),
        make_process(service, pid=300, parent_pid=None, role="node", cmdline=["npm", "run", "dev"]),
        make_process(service, pid=301, parent_pid=300, role="node", cmdline=["vite", "--host", "127.0.0.1"]),
        make_process(service, pid=400, parent_pid=None, role="tauri", cmdline=["npm", "run", "tauri:dev:sidecar"]),
        make_process(service, pid=401, parent_pid=400, role="tauri", cmdline=["cargo", "run"]),
    ]
    monkeypatch.setattr(service, "detect_daily_report_processes", lambda: processes)

    detected = service.list_processes()
    duplicates = [item for item in detected if item.is_duplicate]

    assert [(item.role, item.port) for item in duplicates] == [("api", 8574)]
    assert all(item.risk_level == "safe" for item in detected if item.role in {"node", "tauri"})


def test_duplicate_detection_keeps_independent_api_roots_on_the_same_port(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    api_command = ["python", "-m", "daily_report.main", "api", "--port", "8012"]
    processes = [
        make_process(service, pid=100, parent_pid=1, role="api", cmdline=api_command),
        make_process(service, pid=101, parent_pid=100, role="api", cmdline=["python", "api-worker"], port=8012, is_registered=True),
        make_process(service, pid=200, parent_pid=1, role="api", cmdline=api_command, started_at="2026-07-12T11:00:00"),
        make_process(service, pid=201, parent_pid=200, role="api", cmdline=["python", "api-worker"], port=8012, started_at="2026-07-12T11:00:00", is_registered=True),
    ]
    monkeypatch.setattr(service, "detect_daily_report_processes", lambda: processes)

    duplicates = [item for item in service.list_processes() if item.is_duplicate]

    assert [(item.pid, item.port) for item in duplicates] == [(201, 8012)]


def test_start_collector_does_not_spawn_while_another_request_is_starting(tmp_path, monkeypatch):
    service = make_service(tmp_path)

    @contextmanager
    def busy_guard():
        raise SingleInstanceError("collector start is already in progress")
        yield

    monkeypatch.setattr(service, "_collector_start_guard", busy_guard, raising=False)
    monkeypatch.setattr(service, "check_collector_health", lambda: {"status": "stopped"})
    monkeypatch.setattr(
        "daily_report.service.runtime_process_service.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("Popen must not run while the launch guard is busy"),
    )

    result = service.start_collector_if_not_running()

    assert result == {"started": False, "already_starting": True, "status": "starting"}


def test_start_collector_does_not_trust_a_reused_lock_owner_pid(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    popen_calls = []

    class FakeProcess:
        pid = 5678

        @staticmethod
        def poll():
            return None

    monkeypatch.setattr(service, "check_collector_health", lambda: {"status": "stopped"})
    monkeypatch.setattr(service, "_read_lock_owner_pid", lambda: 4321)
    monkeypatch.setattr("daily_report.service.runtime_process_service.psutil.pid_exists", lambda pid: pid == 4321)
    monkeypatch.setattr(service, "repair_runtime_state", lambda: {"ok": True})
    monkeypatch.setattr(
        service,
        "_wait_for_collector_start",
        lambda process: {"started": True, "status": "running", "pid": process.pid, "launcher_pid": process.pid},
    )
    monkeypatch.setattr("daily_report.service.runtime_process_service.subprocess.Popen", lambda *args, **kwargs: popen_calls.append(args) or FakeProcess())

    result = service.start_collector_if_not_running()

    assert len(popen_calls) == 1
    assert result["started"] is True
    assert result["pid"] == 5678


def test_collector_start_guard_has_a_non_windows_fallback(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    flock_calls = []
    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=8,
        flock=lambda file_descriptor, operation: flock_calls.append((file_descriptor, operation)),
    )
    monkeypatch.setattr("daily_report.service.runtime_process_service.os.name", "posix")
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)

    with service._collector_start_guard():
        pass

    assert [operation for _, operation in flock_calls] == [fake_fcntl.LOCK_EX | fake_fcntl.LOCK_NB, fake_fcntl.LOCK_UN]


def test_wait_for_collector_start_requires_detected_running_health(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    health_results = iter([
        {"status": "stopped"},
        {"status": "stopped"},
        {"status": "running", "pid": 6789},
    ])

    class FakeProcess:
        pid = 5678

        @staticmethod
        def poll():
            return None

    monkeypatch.setattr(service, "check_collector_health", lambda: next(health_results))
    monkeypatch.setattr("daily_report.service.runtime_process_service.time.sleep", lambda _seconds: None)

    result = service._wait_for_collector_start(FakeProcess(), timeout=1)

    assert result == {"started": True, "status": "running", "pid": 6789, "launcher_pid": 5678}


def test_wait_for_collector_start_terminates_launcher_after_timeout(tmp_path, monkeypatch):
    service = make_service(tmp_path)

    class FakeProcess:
        pid = 5678
        terminated = False

        @staticmethod
        def poll():
            return None

        def terminate(self):
            self.terminated = True

        @staticmethod
        def wait(timeout):
            return 0

    process = FakeProcess()
    monotonic_values = iter([0.0, 2.0])
    monkeypatch.setattr(service, "check_collector_health", lambda: {"status": "stopped"})
    monkeypatch.setattr("daily_report.service.runtime_process_service.time.monotonic", lambda: next(monotonic_values))

    result = service._wait_for_collector_start(process, timeout=1)

    assert result["started"] is False
    assert process.terminated is True


def test_summary_uses_registered_processes_without_full_scan(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    monkeypatch.setattr(
        service,
        "detect_daily_report_processes",
        lambda: pytest.fail("summary must not perform a full system process scan"),
    )
    monkeypatch.setattr(service, "list_registered_processes", lambda: [], raising=False)

    summary = service.get_summary()

    assert summary.processes == []


def test_summary_computes_each_health_check_once(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    calls = {"api": 0, "collector": 0, "yasb": 0}

    def api_health(**_kwargs):
        calls["api"] += 1
        return {"status": "running", "pid": None, "port": None, "port_owner_pid": None, "error": None}

    def collector_health(**_kwargs):
        calls["collector"] += 1
        return {"status": "stopped", "pid": None, "message": None}

    def yasb_health(**_kwargs):
        calls["yasb"] += 1
        return {"status": "not_configured"}

    monkeypatch.setattr(service, "list_registered_processes", lambda: [], raising=False)
    monkeypatch.setattr(service, "list_processes", lambda: [])
    monkeypatch.setattr(service, "check_api_health", api_health)
    monkeypatch.setattr(service, "check_collector_health", collector_health)
    monkeypatch.setattr(service, "check_yasb_status", yasb_health)

    service.get_summary()

    assert calls == {"api": 1, "collector": 1, "yasb": 1}


def test_registered_process_snapshot_maps_live_registry_rows(tmp_path):
    service = make_service(tmp_path)
    service.register_current_process("api", port=8765)

    processes = service.list_registered_processes()

    assert len(processes) == 1
    assert processes[0].role == "api"
    assert processes[0].port == 8765
    assert processes[0].is_registered is True


def test_registered_snapshot_rejects_pid_reused_within_same_five_second_window(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    registered_at = datetime(2026, 7, 12, 10, 0, 0)

    class ReusedProcess:
        @staticmethod
        def create_time():
            return (registered_at + timedelta(seconds=1)).timestamp()

    monkeypatch.setattr("daily_report.service.runtime_process_service.psutil.pid_exists", lambda _pid: True)
    monkeypatch.setattr("daily_report.service.runtime_process_service.psutil.Process", lambda _pid: ReusedProcess())

    assert service._registered_process_is_current({"pid": 4321, "started_at": registered_at.isoformat()}) is False


def test_full_scan_filters_candidates_before_reading_expensive_fields(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    requested_attributes: list[list[str]] = []

    def fake_process_iter(attributes):
        requested_attributes.append(attributes)
        return []

    monkeypatch.setattr("daily_report.service.runtime_process_service.psutil.process_iter", fake_process_iter)

    service.detect_daily_report_processes()

    assert requested_attributes == [["pid", "ppid", "name", "cmdline"]]


def test_stop_collector_uses_registered_snapshot_without_full_scan(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    collector = make_process(
        service,
        pid=4321,
        parent_pid=1,
        role="collector",
        cmdline=["python", "-m", "daily_report.main", "run"],
        is_registered=True,
    )
    stopped: list[int] = []
    monkeypatch.setattr(service, "list_registered_processes", lambda: [collector])
    monkeypatch.setattr(
        service,
        "list_processes",
        lambda: pytest.fail("stopping a registered collector must not perform a full system scan"),
    )
    monkeypatch.setattr(
        service,
        "_stop_process",
        lambda pid, *, force, known_processes=None: stopped.append(pid)
        or {"pid": pid, "role": "collector", "action": "terminate"},
    )

    result = service.stop_collector_gracefully()

    assert stopped == [4321]
    assert result["stopped"][0]["action"] == "terminate"


def test_stop_registered_process_uses_quick_snapshot_before_full_scan(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    collector = make_process(
        service,
        pid=4321,
        parent_pid=1,
        role="collector",
        cmdline=["python", "-m", "daily_report.main", "run"],
        is_registered=True,
    )

    class FakeProcess:
        @staticmethod
        def create_time():
            return datetime.fromisoformat(collector.started_at or "").timestamp()

        @staticmethod
        def terminate():
            return None

        @staticmethod
        def wait(timeout):
            return 0

    monkeypatch.setattr(service, "list_registered_processes", lambda: [collector])
    monkeypatch.setattr(
        service,
        "list_processes",
        lambda: pytest.fail("a registered process must not fall back to a full system scan"),
    )
    monkeypatch.setattr("daily_report.service.runtime_process_service.psutil.Process", lambda _pid: FakeProcess())

    result = service.terminate_process(4321)

    assert result == {
        "pid": 4321,
        "role": "collector",
        "action": "terminate",
        "cmdline_preview": "python -m daily_report.main run",
    }


def test_stop_registered_process_rechecks_creation_time_before_signalling(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    collector = make_process(
        service,
        pid=4321,
        parent_pid=1,
        role="collector",
        cmdline=["python", "-m", "daily_report.main", "run"],
        is_registered=True,
    )

    class ReusedProcess:
        terminate_called = False

        @staticmethod
        def create_time():
            started_at = datetime.fromisoformat(collector.started_at or "")
            return (started_at + timedelta(seconds=1)).timestamp()

        def terminate(self):
            self.terminate_called = True

    process = ReusedProcess()
    monkeypatch.setattr(service, "list_registered_processes", lambda: [collector])
    monkeypatch.setattr("daily_report.service.runtime_process_service.psutil.Process", lambda _pid: process)

    with pytest.raises(RuntimeError, match="identity changed"):
        service.terminate_process(4321)

    assert process.terminate_called is False


def test_summary_with_registered_api_does_not_enumerate_system_ports(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    api = make_process(
        service,
        pid=4321,
        parent_pid=1,
        role="api",
        cmdline=["python", "-m", "daily_report.main", "api", "--port", "8765"],
        port=8765,
        is_registered=True,
    )

    class FakeResponse:
        @staticmethod
        def read():
            return b'{"ok": true}'

        def __enter__(self):
            return self

        @staticmethod
        def __exit__(_exc_type, _exc, _traceback):
            return False

    monkeypatch.setattr(service, "list_registered_processes", lambda: [api])
    monkeypatch.setattr(
        "daily_report.service.runtime_process_service.psutil.net_connections",
        lambda **_kwargs: pytest.fail("quick summary must not enumerate system network connections"),
    )
    monkeypatch.setattr(
        "daily_report.service.runtime_process_service.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    summary = service.get_summary()

    assert summary.api_status == "running"
    assert summary.api_pid == 4321


def test_summary_downgrades_running_components_when_collector_process_is_absent(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    with service._connect() as conn:
        CollectorStateRepository(conn).mark_running("foreground")

    monkeypatch.setattr(service, "list_registered_processes", lambda: [])
    monkeypatch.setattr(
        service,
        "check_api_health",
        lambda **_kwargs: {"status": "stopped", "pid": None, "port": 8765, "port_owner_pid": None, "error": None},
    )
    monkeypatch.setattr(
        service,
        "check_collector_health",
        lambda **_kwargs: {"status": "stopped", "pid": None, "message": None},
    )
    monkeypatch.setattr(service, "check_database_health", lambda **_kwargs: {"status": "ok"})
    monkeypatch.setattr(service, "check_yasb_status", lambda **_kwargs: {"status": "not_configured"})

    summary = service.get_summary()
    foreground = next(component for component in summary.components if component.name == "foreground")

    assert foreground.status == "stopped"
    assert foreground.enabled is True
