from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from daily_report.storage.database import SqliteConnectionFactory
from daily_report.storage.repositories.report_repository import DailyReportRepository, DailyReportRecord


@dataclass(frozen=True)
class SaveReportCommand:
    date: str
    model_name: str
    prompt_text: str
    report_markdown: str
    report_type: str = 'daily'
    template_name: str = 'daily_standard'
    model_provider: str = 'deepseek'
    material_snapshot_json: str | None = None
    material_summary: str | None = None
    source_counts: dict[str, Any] | None = None


class ReportStore:
    """Storage adapter for generated daily reports."""

    def __init__(self, connection_factory: SqliteConnectionFactory):
        self.connection_factory = connection_factory

    def save(self, command: SaveReportCommand) -> int:
        with self.connection_factory.connect() as conn:
            repo = DailyReportRepository(conn)
            return repo.save_report(
                date=command.date,
                model_name=command.model_name,
                prompt_text=command.prompt_text,
                report_markdown=command.report_markdown,
                report_type=command.report_type,
                template_name=command.template_name,
                model_provider=command.model_provider,
                material_snapshot_json=command.material_snapshot_json,
                material_summary=command.material_summary,
                source_counts=command.source_counts,
            )

    def latest_by_date(self, date: str) -> DailyReportRecord | None:
        with self.connection_factory.connect() as conn:
            return DailyReportRepository(conn).get_latest_by_date(date)

    def get_by_id(self, report_id: int) -> DailyReportRecord | None:
        with self.connection_factory.connect() as conn:
            return DailyReportRepository(conn).get_by_id(report_id)

    def list_by_date(self, date: str) -> list[DailyReportRecord]:
        with self.connection_factory.connect() as conn:
            return DailyReportRepository(conn).list_by_date(date)

    def list_reports(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[DailyReportRecord]:
        with self.connection_factory.connect() as conn:
            return DailyReportRepository(conn).list_reports(start_date=start_date, end_date=end_date)

    def delete(self, report_id: int) -> None:
        with self.connection_factory.connect() as conn:
            DailyReportRepository(conn).delete_report(report_id)
