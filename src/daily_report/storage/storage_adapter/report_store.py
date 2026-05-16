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
    material_summary: str | None = None
    source_counts: dict[str, Any] | None = None


class ReportStore:
    """Storage adapter for generated daily reports."""

    def __init__(self, connection_factory: SqliteConnectionFactory):
        self.connection_factory = connection_factory

    def save(self, command: SaveReportCommand) -> int:
        with self.connection_factory.connect() as conn:
            repo = DailyReportRepository(conn)
            return repo.create(
                date=command.date,
                model_name=command.model_name,
                prompt_text=command.prompt_text,
                report_markdown=command.report_markdown,
                material_summary=command.material_summary,
                source_counts=command.source_counts,
            )

    def latest_by_date(self, date: str) -> DailyReportRecord | None:
        with self.connection_factory.connect() as conn:
            return DailyReportRepository(conn).get_latest_by_date(date)

    def list_by_date(self, date: str) -> list[DailyReportRecord]:
        with self.connection_factory.connect() as conn:
            return DailyReportRepository(conn).list_by_date(date)
