from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DailyReportRecord:
    id: int
    date: str
    model_name: str
    prompt_text: str
    report_markdown: str
    material_summary: str | None
    source_counts: dict[str, Any]
    created_at: str


class DailyReportRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
            self,
            *,
            date: str,
            model_name: str,
            prompt_text: str,
            report_markdown: str,
            material_summary: str | None = None,
            source_counts: dict[str, Any] | None = None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO daily_reports (
                date,
                model_name,
                prompt_text,
                report_markdown,
                material_summary,
                source_counts_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                model_name,
                prompt_text,
                report_markdown,
                material_summary,
                json.dumps(source_counts or {}, ensure_ascii=False),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_latest_by_date(self, date: str) -> DailyReportRecord | None:
        cursor = self.conn.execute(
            """
            SELECT
                id,
                date,
                model_name,
                prompt_text,
                report_markdown,
                material_summary,
                source_counts_json,
                created_at
            FROM daily_reports
            WHERE date = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (date,),
        )
        row = cursor.fetchone()
        return self._to_record(row) if row else None

    def list_by_date(self, date: str) -> list[DailyReportRecord]:
        cursor = self.conn.execute(
            """
            SELECT
                id,
                date,
                model_name,
                prompt_text,
                report_markdown,
                material_summary,
                source_counts_json,
                created_at
            FROM daily_reports
            WHERE date = ?
            ORDER BY created_at DESC
            """,
            (date,),
        )
        return [self._to_record(row) for row in cursor.fetchall()]

    def list_recent(self, limit: int = 30) -> list[DailyReportRecord]:
        cursor = self.conn.execute(
            """
            SELECT
                id,
                date,
                model_name,
                prompt_text,
                report_markdown,
                material_summary,
                source_counts_json,
                created_at
            FROM daily_reports
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._to_record(row) for row in cursor.fetchall()]

    @staticmethod
    def _to_record(row: sqlite3.Row) -> DailyReportRecord:
        return DailyReportRecord(
            id=row["id"],
            date=row["date"],
            model_name=row["model_name"],
            prompt_text=row["prompt_text"],
            report_markdown=row["report_markdown"],
            material_summary=row["material_summary"],
            source_counts=json.loads(row["source_counts_json"] or "{}"),
            created_at=row["created_at"],
        )
