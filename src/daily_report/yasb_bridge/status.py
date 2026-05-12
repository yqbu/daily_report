from __future__ import annotations

import json
import sqlite3
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from daily_report.storage.database import default_db_path, create_connection
from daily_report.storage.repositories import AppSessionRepository


def fmt_seconds(sec: int | float | None) -> str:
    sec = int(sec or 0)
    h, rem = divmod(sec, 3600)
    m, _ = divmod(rem, 60)

    if h > 0:
        return f'{h}h{m:02d}m'
    return f'{m}m'


def empty_status(message: str) -> dict[str, Any]:
    return {
        'active_time': '0m',
        'total_time': '0m',
        'top_apps_inline': message,
        'session_count': 0,
        'tooltip': message,
    }


def build_status_payload(
    *,
    target_date: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    db_path = Path(default_db_path())

    if not db_path.exists():
        return empty_status('数据库尚未创建')

    day = target_date or date_cls.today().isoformat()

    try:
        conn = create_connection(db_path)
        repo = AppSessionRepository(conn)

        top_apps = repo.get_today_top_apps(day, limit=limit)

        total_row = conn.execute(
            """
            SELECT
                COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
                COALESCE(SUM(active_duration_sec), 0) AS total_active_duration_sec,
                COUNT(*) AS session_count
            FROM app_sessions
            WHERE date = ?
            """,
            (day,),
        ).fetchone()

    except sqlite3.Error as exc:
        return empty_status(f'SQLite 错误：{exc}')

    total_duration_sec = total_row['total_duration_sec'] if total_row else 0
    total_active_duration_sec = total_row['total_active_duration_sec'] if total_row else 0
    session_count = total_row['session_count'] if total_row else 0

    top_apps_inline = ' · '.join(
        f'{row['app_name']} {fmt_seconds(row['total_active_duration_sec'])}'
        for row in top_apps[:3]
    )

    if not top_apps_inline:
        top_apps_inline = '暂无数据'

    tooltip_lines = [
        f'日期: {day}',
        f'今日总时长: {fmt_seconds(total_duration_sec)}',
        f'今日活跃: {fmt_seconds(total_active_duration_sec)}',
        'Top 应用: ',
    ]

    for idx, row in enumerate(top_apps, start=1):
        tooltip_lines.append(
            f'{idx}. {row['app_name']} '
            f'{fmt_seconds(row['total_active_duration_sec'])} '
            f'({row['session_count']} 段)'
        )

    return {
        'active_time': fmt_seconds(total_active_duration_sec),
        'total_time': fmt_seconds(total_duration_sec),
        'top_apps_inline': top_apps_inline,
        'session_count': int(session_count or 0),
        'tooltip': '\n'.join(tooltip_lines),
    }


def print_status(
    *,
    target_date: str | None = None,
    limit: int = 5,
    as_json: bool = True,
) -> None:
    payload = build_status_payload(
        target_date=target_date,
        limit=limit,
    )

    if as_json:
        print(json.dumps(payload, ensure_ascii=True))
        return

    print(payload['tooltip'])