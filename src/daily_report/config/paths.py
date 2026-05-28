from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
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


@lru_cache(maxsize=1)
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


def get_installed_share_root() -> Path:
    """Return the platform-independent data-files install location used by wheels."""
    return Path(sys.prefix) / 'share' / 'daily-report'


def get_runtime_paths() -> RuntimePaths:
    return _get_runtime_paths(
        os.getenv('DAILY_REPORT_DATA_DIR'),
        os.getenv('DAILY_REPORT_LOG_DIR'),
        os.getenv('DAILY_REPORT_OUTPUT_DIR'),
    )


@lru_cache(maxsize=16)
def _get_runtime_paths(
    data_dir_value: str | None,
    log_dir_value: str | None,
    output_dir_value: str | None,
) -> RuntimePaths:
    project_root = get_project_root()

    data_dir = Path(data_dir_value).expanduser().resolve() if data_dir_value else project_root / 'data'

    data_dir.mkdir(parents=True, exist_ok=True)

    log_dir = Path(log_dir_value).expanduser().resolve() if log_dir_value else project_root / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    output_dir = Path(output_dir_value).expanduser() if output_dir_value else project_root / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    return RuntimePaths(
        project_root=project_root,
        data_dir=data_dir,
        db_path=data_dir / 'daily_report.db',
        local_settings_path=data_dir / 'local_settings.json',
        status_json_path=data_dir / 'status.json',
        log_dir=log_dir,
        output_dir=output_dir
    )
