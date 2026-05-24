from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DailyReportRecord:
    id: int
    date: str
    report_type: str
    template_name: str
    model_provider: str
    model_name: str
    prompt_text: str
    report_markdown: str
    material_snapshot_json: str | None
    material_summary: str | None
    source_counts: dict[str, Any]
    created_at: str
    updated_at: str


class DailyReportRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_report(
        self,
        *,
        date: str,
        model_name: str,
        prompt_text: str,
        report_markdown: str,
        report_type: str = 'daily',
        template_name: str = 'daily_standard',
        model_provider: str = 'deepseek',
        material_snapshot_json: str | None = None,
        material_summary: str | None = None,
        source_counts: dict[str, Any] | None = None,
    ) -> int:
        now = _now()
        cursor = self.conn.execute(
            """
            INSERT INTO daily_reports (
                date, report_type, template_name, model_provider, model_name,
                prompt_text, report_markdown, material_snapshot_json,
                material_summary, source_counts_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                report_type,
                template_name,
                model_provider,
                model_name,
                prompt_text,
                report_markdown,
                material_snapshot_json,
                material_summary,
                json.dumps(source_counts or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

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
        return self.save_report(
            date=date,
            model_name=model_name,
            prompt_text=prompt_text,
            report_markdown=report_markdown,
            material_summary=material_summary,
            source_counts=source_counts,
        )

    def get_latest_by_date(self, date: str) -> DailyReportRecord | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM daily_reports
            WHERE date = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (date,),
        ).fetchone()
        return self._to_record(row) if row else None

    def list_reports(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[DailyReportRecord]:
        clauses = ['1 = 1']
        params: list[Any] = []
        if start_date:
            clauses.append('date >= ?')
            params.append(start_date)
        if end_date:
            clauses.append('date <= ?')
            params.append(end_date)
        sql = f"""
            SELECT *
            FROM daily_reports
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, id DESC
        """
        if limit is not None:
            sql += ' LIMIT ? OFFSET ?'
            params.extend([int(limit), int(offset)])
        return [self._to_record(row) for row in self.conn.execute(sql, tuple(params)).fetchall()]

    def delete_report(self, report_id: int) -> None:
        self.conn.execute("DELETE FROM daily_reports WHERE id = ?", (int(report_id),))
        self.conn.commit()

    def get_by_id(self, report_id: int) -> DailyReportRecord | None:
        row = self.conn.execute(
            "SELECT * FROM daily_reports WHERE id = ?",
            (int(report_id),),
        ).fetchone()
        return self._to_record(row) if row else None

    def list_by_date(self, date: str) -> list[DailyReportRecord]:
        return self.list_reports(start_date=date, end_date=date)

    def list_recent(self, limit: int = 30) -> list[DailyReportRecord]:
        return self.list_reports(limit=limit)

    @staticmethod
    def _to_record(row: sqlite3.Row) -> DailyReportRecord:
        source_counts_json = _row_get(row, 'source_counts_json', '{}') or '{}'
        try:
            source_counts = json.loads(source_counts_json)
        except json.JSONDecodeError:
            source_counts = {}
        return DailyReportRecord(
            id=int(row['id']),
            date=str(row['date']),
            report_type=str(_row_get(row, 'report_type', 'daily') or 'daily'),
            template_name=str(_row_get(row, 'template_name', 'daily_standard') or 'daily_standard'),
            model_provider=str(_row_get(row, 'model_provider', 'deepseek') or 'deepseek'),
            model_name=str(row['model_name']),
            prompt_text=str(row['prompt_text']),
            report_markdown=str(row['report_markdown']),
            material_snapshot_json=_row_get(row, 'material_snapshot_json'),
            material_summary=_row_get(row, 'material_summary'),
            source_counts=source_counts if isinstance(source_counts, dict) else {},
            created_at=str(row['created_at']),
            updated_at=str(_row_get(row, 'updated_at', row['created_at']) or row['created_at']),
        )


def _row_get(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    return row[key] if key in row.keys() else default


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
