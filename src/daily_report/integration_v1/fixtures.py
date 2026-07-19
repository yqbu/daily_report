from __future__ import annotations

from daily_report.integration_v1.projection import ProjectedReport

FIXTURE_ID = "daily-report-v1-synthetic-20260718"


class SyntheticIntegrationProjection:
    def __init__(self) -> None:
        reports = (
            ProjectedReport(
                date="2026-07-14",
                report_id="synthetic-report-4",
                summary="Synthetic sparse-range summary.",
                source_updated_at="2026-07-14T08:00:00.000Z",
            ),
            ProjectedReport(
                date="2026-07-16",
                report_id="synthetic-report-6",
                summary="Synthetic continuous-range start.",
                source_updated_at="2026-07-16T08:00:00.000Z",
            ),
            ProjectedReport(
                date="2026-07-17",
                report_id="synthetic-report-7",
                summary=None,
                source_updated_at="2026-07-17T08:00:00.000Z",
            ),
            ProjectedReport(
                date="2026-07-18",
                report_id="synthetic-report-8",
                summary="Synthetic current summary.",
                source_updated_at="2026-07-17T23:59:00.000Z",
            ),
        )
        self._reports = {report.date: report for report in reports}

    def get_report(self, target_date: str) -> ProjectedReport | None:
        return self._reports.get(target_date)

    def list_reports(
        self,
        start_date: str,
        end_date: str,
        limit: int,
    ) -> list[ProjectedReport]:
        return [
            report
            for target_date, report in sorted(self._reports.items())
            if start_date <= target_date <= end_date
        ][:limit]
