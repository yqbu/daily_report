from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any


class RuntimeProcessRepository:
    """Repository for the optional runtime process registry."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def register_process(
        self,
        *,
        role: str,
        pid: int,
        parent_pid: int | None = None,
        process_name: str | None = None,
        exe_path: str | None = None,
        cmdline: list[str] | None = None,
        cwd: str | None = None,
        port: int | None = None,
        db_path: str | None = None,
        lock_path: str | None = None,
        started_by: str | None = None,
        status: str = 'running',
        started_at: str | None = None,
        last_error: str | None = None,
    ) -> None:
        now = _now()
        self.conn.execute(
            """
            INSERT INTO runtime_processes (
                role, pid, parent_pid, process_name, exe_path, cmdline, cwd, port,
                db_path, lock_path, started_by, status, heartbeat_at, started_at,
                last_error, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(role, pid)
            DO UPDATE SET
                parent_pid = excluded.parent_pid,
                process_name = excluded.process_name,
                exe_path = excluded.exe_path,
                cmdline = excluded.cmdline,
                cwd = excluded.cwd,
                port = excluded.port,
                db_path = excluded.db_path,
                lock_path = excluded.lock_path,
                started_by = excluded.started_by,
                status = excluded.status,
                heartbeat_at = excluded.heartbeat_at,
                started_at = COALESCE(runtime_processes.started_at, excluded.started_at),
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (
                role,
                int(pid),
                parent_pid,
                process_name,
                exe_path,
                json.dumps(cmdline or [], ensure_ascii=False),
                cwd,
                port,
                db_path,
                lock_path,
                started_by,
                status,
                now,
                started_at or now,
                last_error,
                now,
                now,
            ),
        )
        self.conn.commit()

    def update_heartbeat(
        self,
        role: str,
        pid: int,
        *,
        status: str = 'running',
        last_error: str | None = None,
    ) -> None:
        now = _now()
        self.conn.execute(
            """
            UPDATE runtime_processes
            SET heartbeat_at = ?, status = ?, last_error = ?, updated_at = ?
            WHERE role = ? AND pid = ?
            """,
            (now, status, last_error, now, role, int(pid)),
        )
        self.conn.commit()

    def update_status(
        self,
        role: str,
        pid: int,
        status: str,
        last_error: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE runtime_processes
            SET status = ?, last_error = ?, updated_at = ?
            WHERE role = ? AND pid = ?
            """,
            (status, last_error, _now(), role, int(pid)),
        )
        self.conn.commit()

    def mark_exited(self, pid: int) -> None:
        self.conn.execute(
            """
            UPDATE runtime_processes
            SET status = 'exited', updated_at = ?
            WHERE pid = ? AND status <> 'exited'
            """,
            (_now(), int(pid)),
        )
        self.conn.commit()

    def list_active(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT *
                FROM runtime_processes
                WHERE status NOT IN ('exited', 'stopped')
                ORDER BY role ASC, pid ASC
                """
            ).fetchall()
        ]

    def list_by_role(self, role: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT *
                FROM runtime_processes
                WHERE role = ?
                ORDER BY updated_at DESC, pid ASC
                """,
                (role,),
            ).fetchall()
        ]

    def cleanup_stale_records(self, existing_pids: set[int]) -> int:
        active_rows = self.list_active()
        stale_pids = [int(row['pid']) for row in active_rows if int(row['pid']) not in existing_pids]
        if not stale_pids:
            return 0
        placeholders = ','.join('?' for _ in stale_pids)
        self.conn.execute(
            f"""
            UPDATE runtime_processes
            SET status = 'exited', updated_at = ?
            WHERE pid IN ({placeholders})
            """,
            (_now(), *stale_pids),
        )
        self.conn.commit()
        return len(stale_pids)


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
