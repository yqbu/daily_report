from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any


class CollectorStateRepository:
    """Repository for collector health and lifecycle state."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert_state(
        self,
        collector_name: str,
        *,
        enabled: bool = True,
        status: str = 'unknown',
        last_success_at: str | None = None,
        last_error_at: str | None = None,
        last_error_message: str | None = None,
        records_collected: int | None = None,
    ) -> None:
        existing = self.get_by_name(collector_name)
        current_records = int(existing['records_collected']) if existing and records_collected is None else 0
        self.conn.execute(
            """
            INSERT INTO collector_state (
                collector_name, enabled, status, last_success_at, last_error_at,
                last_error_message, records_collected, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(collector_name)
            DO UPDATE SET
                enabled = excluded.enabled,
                status = excluded.status,
                last_success_at = COALESCE(excluded.last_success_at, collector_state.last_success_at),
                last_error_at = COALESCE(excluded.last_error_at, collector_state.last_error_at),
                last_error_message = COALESCE(excluded.last_error_message, collector_state.last_error_message),
                records_collected = excluded.records_collected,
                updated_at = excluded.updated_at
            """,
            (
                collector_name,
                int(enabled),
                status,
                last_success_at,
                last_error_at,
                last_error_message,
                int(records_collected if records_collected is not None else current_records),
                _now(),
            ),
        )
        self.conn.commit()

    def mark_running(self, collector_name: str, *, enabled: bool = True) -> None:
        self.upsert_state(
            collector_name,
            enabled=enabled,
            status='running',
            last_success_at=_now(),
            last_error_message='',
        )

    def mark_stopped(self, collector_name: str, *, enabled: bool = True) -> None:
        self.upsert_state(collector_name, enabled=enabled, status='stopped')

    def mark_error(self, collector_name: str, message: str, *, enabled: bool = True) -> None:
        self.upsert_state(
            collector_name,
            enabled=enabled,
            status='error',
            last_error_at=_now(),
            last_error_message=message[:1000],
        )

    def increment_records(self, collector_name: str, count: int = 1) -> None:
        row = self.get_by_name(collector_name)
        current = int(row['records_collected']) if row else 0
        self.upsert_state(
            collector_name,
            status=str(row['status']) if row else 'running',
            records_collected=current + int(count),
            last_success_at=_now(),
        )

    def get_by_name(self, collector_name: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM collector_state WHERE collector_name = ?",
            (collector_name,),
        ).fetchone()

    def list_states(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT *
                FROM collector_state
                ORDER BY collector_name ASC
                """
            ).fetchall()
        ]


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
