from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from daily_report.integration_v1.projection import (
    IntegrationProjectionService,
    IntegrationProjectionUnavailable,
)
from daily_report.storage.read_models.integration_report_reader import (
    ReadonlyIntegrationReportReader,
)


def create_report_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            report_type TEXT NOT NULL DEFAULT 'daily',
            template_name TEXT NOT NULL DEFAULT 'daily_standard',
            model_provider TEXT NOT NULL,
            model_name TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            report_markdown TEXT NOT NULL,
            material_snapshot_json TEXT,
            material_summary TEXT,
            source_counts_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        """
        INSERT INTO daily_reports (
            date, model_provider, model_name, prompt_text, report_markdown,
            material_snapshot_json, created_at, updated_at
        ) VALUES (?, 'synthetic', 'synthetic', ?, ?, ?, ?, ?)
        """,
        [
            (
                "2026-07-17",
                "private prompt",
                "# Daily\n\n## Summary\n\nOlder summary.\n\n## Details\n\nPrivate detail.",
                '{"private": true}',
                "2026-07-17T08:00:00+08:00",
                "2026-07-17T08:01:00+08:00",
            ),
            (
                "2026-07-18",
                "private prompt",
                "# Daily\n\n## Summary\n\nInitial summary.",
                '{"private": true}',
                "2026-07-18T08:00:00+08:00",
                "2026-07-18T08:01:00+08:00",
            ),
            (
                "2026-07-18",
                "new private prompt",
                "# Daily\n\n## Summary\n\nNewest **deterministic** summary.\n\n- Hidden detail",
                '{"new_private": true}',
                "2026-07-18T09:00:00+08:00",
                "2026-07-18T09:01:00+08:00",
            ),
        ],
    )
    connection.commit()
    connection.close()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_projection_reads_latest_reports_without_mutating_database(tmp_path: Path) -> None:
    database = tmp_path / "synthetic.db"
    create_report_database(database)
    before_hash = sha256(database)
    projection = IntegrationProjectionService(ReadonlyIntegrationReportReader(database))

    daily = projection.get_report("2026-07-18")
    ranged = projection.list_reports("2026-07-17", "2026-07-18", 90)

    assert daily is not None
    assert daily.report_id == "report-3"
    assert daily.date == "2026-07-18"
    assert daily.summary == "Newest deterministic summary."
    assert daily.source_updated_at == "2026-07-18T01:01:00.000Z"
    assert [(item.date, item.report_id) for item in ranged] == [
        ("2026-07-17", "report-1"),
        ("2026-07-18", "report-3"),
    ]
    assert sha256(database) == before_hash
    assert not database.with_name(database.name + "-wal").exists()
    assert not database.with_name(database.name + "-shm").exists()


def test_projection_missing_database_fails_without_creating_it(tmp_path: Path) -> None:
    database = tmp_path / "missing.db"
    projection = IntegrationProjectionService(ReadonlyIntegrationReportReader(database))

    with pytest.raises(IntegrationProjectionUnavailable):
        projection.get_report("2026-07-18")

    assert not database.exists()


def test_historical_summary_conversion_is_deterministic_bounded_and_has_no_llm_dependency() -> None:
    markdown = "# Daily\n\n## Summary\n\n" + ("word " * 5000) + "\n\n## Details\n\nprivate"

    first = IntegrationProjectionService.summarize_markdown(markdown)
    second = IntegrationProjectionService.summarize_markdown(markdown)

    assert first == second
    assert first is not None
    assert len(first) <= 16384
    assert "Details" not in first
    assert "private" not in first


def test_projection_boundary_does_not_import_generation_or_existing_mutating_services() -> None:
    projection_source = Path("src/daily_report/integration_v1/projection.py").read_text(
        encoding="utf-8"
    )
    reader_source = Path(
        "src/daily_report/storage/read_models/integration_report_reader.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "DeepSeekClient",
        "ReportService",
        "OverviewService",
        "init_database",
        "create_connection",
        "prompt_text",
        "material_snapshot_json",
        "SELECT *",
    )
    assert all(term not in projection_source for term in forbidden)
    assert all(term not in reader_source for term in forbidden)
