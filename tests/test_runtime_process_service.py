from __future__ import annotations

from daily_report.service.runtime_process_service import RuntimeProcessInfo, RuntimeProcessService
from daily_report.storage.database import create_connection, init_database
from daily_report.storage.repositories.runtime_process_repository import RuntimeProcessRepository


def make_service(tmp_path) -> RuntimeProcessService:
    project_root = tmp_path / "daily_report"
    project_root.mkdir()
    return RuntimeProcessService(db_path=tmp_path / "daily_report.db", project_root=project_root)


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
