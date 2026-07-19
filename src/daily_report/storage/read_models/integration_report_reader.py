from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


class ProjectionUnavailableError(RuntimeError):
    """只读投影当前不可用."""


@dataclass(frozen=True)
class ReadonlyReportRow:
    id: int
    date: str
    report_markdown: str
    created_at: str
    updated_at: str | None


class ReadonlyIntegrationReportReader:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def get_latest_by_date(self, target_date: str) -> ReadonlyReportRow | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT id, date, report_markdown, created_at, updated_at
                    FROM daily_reports
                    WHERE date = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """,
                    (target_date,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise ProjectionUnavailableError("Integration projection is unavailable.") from exc
        return self._to_row(row) if row is not None else None

    def list_latest_by_date(
        self,
        start_date: str,
        end_date: str,
        limit: int,
    ) -> list[ReadonlyReportRow]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT id, date, report_markdown, created_at, updated_at
                    FROM (
                        SELECT
                            id,
                            date,
                            report_markdown,
                            created_at,
                            updated_at,
                            ROW_NUMBER() OVER (
                                PARTITION BY date
                                ORDER BY created_at DESC, id DESC
                            ) AS row_number
                        FROM daily_reports
                        WHERE date >= ? AND date <= ?
                    )
                    WHERE row_number = 1
                    ORDER BY date ASC
                    LIMIT ?
                    """,
                    (start_date, end_date, int(limit)),
                ).fetchall()
        except sqlite3.Error as exc:
            raise ProjectionUnavailableError("Integration projection is unavailable.") from exc
        return [self._to_row(row) for row in rows]

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, check_same_thread=True)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            connection.execute("PRAGMA busy_timeout = 2000")
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _to_row(row: sqlite3.Row) -> ReadonlyReportRow:
        return ReadonlyReportRow(
            id=int(row["id"]),
            date=str(row["date"]),
            report_markdown=str(row["report_markdown"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]) if row["updated_at"] else None,
        )
