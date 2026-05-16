from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    project_root: Path
    data_dir: Path
    db_path: Path
    local_settings_path: Path
    status_json_path: Path
    log_dir: Path
    output_dir: Path


def get_project_root() -> Path:
    """
    当前文件位置：
    src/daily_report/config/paths.py

    parents[0] = config
    parents[1] = daily_report
    parents[2] = src
    parents[3] = project root
    """
    return Path(__file__).resolve().parents[3]


def get_runtime_paths() -> RuntimePaths:
    project_root = get_project_root()

    data_dir = Path(
        os.getenv("DAILY_REPORT_DATA_DIR", project_root / "data")
    ).resolve()

    data_dir.mkdir(parents=True, exist_ok=True)

    log_dir = Path(
        os.getenv("DAILY_REPORT_LOG_DIR", project_root / "logs")
    ).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    output_dir = Path(
        os.getenv("DAILY_REPORT_OUTPUT_DIR", project_root / "output")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    return RuntimePaths(
        project_root=project_root,
        data_dir=data_dir,
        db_path=data_dir / "daily_report.db",
        local_settings_path=data_dir / "local_settings.json",
        status_json_path=data_dir / "status.json",
        log_dir=log_dir,
        output_dir=output_dir
    )