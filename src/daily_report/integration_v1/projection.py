from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from daily_report.storage.read_models.integration_report_reader import (
    ProjectionUnavailableError,
    ReadonlyIntegrationReportReader,
    ReadonlyReportRow,
)

MAX_SUMMARY_LENGTH = 16_384
_SUMMARY_HEADING = re.compile(r"^#{1,6}\s*(summary|摘要|总结)\s*$", re.IGNORECASE)
_ANY_HEADING = re.compile(r"^#{1,6}\s+")


class IntegrationProjectionUnavailable(RuntimeError):
    """公开只读投影当前不可用."""


@dataclass(frozen=True)
class ProjectedReport:
    date: str
    report_id: str
    summary: str | None
    source_updated_at: str | None


class IntegrationProjection(Protocol):
    def get_report(self, target_date: str) -> ProjectedReport | None: ...

    def list_reports(
        self,
        start_date: str,
        end_date: str,
        limit: int,
    ) -> list[ProjectedReport]: ...


class IntegrationProjectionService:
    def __init__(self, reader: ReadonlyIntegrationReportReader):
        self.reader = reader

    def get_report(self, target_date: str) -> ProjectedReport | None:
        try:
            row = self.reader.get_latest_by_date(target_date)
        except ProjectionUnavailableError as exc:
            raise IntegrationProjectionUnavailable from exc
        return self._project(row) if row is not None else None

    def list_reports(
        self,
        start_date: str,
        end_date: str,
        limit: int,
    ) -> list[ProjectedReport]:
        try:
            rows = self.reader.list_latest_by_date(start_date, end_date, limit)
        except ProjectionUnavailableError as exc:
            raise IntegrationProjectionUnavailable from exc
        return [self._project(row) for row in rows]

    @classmethod
    def _project(cls, row: ReadonlyReportRow) -> ProjectedReport:
        return ProjectedReport(
            date=row.date,
            report_id=f"report-{row.id}",
            summary=cls.summarize_markdown(row.report_markdown),
            source_updated_at=_to_utc_milliseconds(row.updated_at or row.created_at),
        )

    @staticmethod
    def summarize_markdown(markdown: str | None) -> str | None:
        if not markdown or not markdown.strip():
            return None

        lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        summary_start = next(
            (index + 1 for index, line in enumerate(lines) if _SUMMARY_HEADING.match(line.strip())),
            None,
        )
        candidates = lines[summary_start:] if summary_start is not None else lines
        paragraph: list[str] = []
        started = False

        for raw_line in candidates:
            line = raw_line.strip()
            if _ANY_HEADING.match(line):
                if started:
                    break
                continue
            if not line:
                if started:
                    break
                continue
            if line.startswith(("- ", "* ", "+ ")):
                if started:
                    break
                continue
            paragraph.append(line)
            started = True

        if not paragraph:
            return None

        summary = _strip_inline_markdown(" ".join(paragraph)).strip()
        if not summary:
            return None
        return summary[:MAX_SUMMARY_LENGTH].rstrip()


def _strip_inline_markdown(value: str) -> str:
    value = re.sub(r"!\[([^]]*)]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", value)
    value = re.sub(r"(`{1,3}|\*\*|__|~~)", "", value)
    return re.sub(r"\s+", " ", value)


def _to_utc_milliseconds(value: str | None) -> str | None:
    if not value:
        return None
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if instant.tzinfo is None:
        instant = instant.astimezone()
    return instant.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
