from __future__ import annotations

import json
import sqlite3
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from daily_report.storage.database import default_db_path, create_connection
from daily_report.storage.repositories import AppSessionRepository
from daily_report.yasb_bridge.collector_status import build_collector_status_payload


def fmt_seconds(sec: int | float | None) -> str:
    sec = int(sec or 0)
    h, rem = divmod(sec, 3600)
    m, _ = divmod(rem, 60)

    if h > 0:
        return f'{h}h{m:02d}m'
    return f'{m}m'


def fmt_top_apps(apps: list[dict[str, Any]], with_header: bool = True) -> str:
    """
    apps:
        [
            {"name": "Microsoft Edge", "duration": "31m", "count": 157},
            {"name": "PyCharm", "duration": "16m", "count": 39},
        ]
    """
    if not apps:
        return "No app usage data."

    rank_width = max(len("No."), len(f"{len(apps)}."))
    name_width = max(len("Top App"), max(len(item["app_name"]) for item in apps))
    duration_width = max(len("Time"), max(len(fmt_seconds(item['total_active_duration_sec'])) for item in apps))
    count_texts = [f"{item['session_count']} 次" for item in apps]
    count_width = max(len("Count"), max(len(text) for text in count_texts))

    lines = []

    if with_header:
        header = (
            f"{'No.':<{rank_width}} "
            f"{'Top App':<{name_width}}  "
            f"{'Time':>{duration_width}}  "
            f"{'Count':>{count_width}}"
        )
        lines.append(header)
        lines.append("-" * (len(header) + 2))

    for idx, item in enumerate(apps, start=1):
        idx_text = f"{idx}."
        name = item["app_name"]
        duration = fmt_seconds(item['total_active_duration_sec'])
        count_text = f"{item['session_count']} 次"

        line = (
            f"{idx_text:<{rank_width}} "
            f"{name:<{name_width}}  "
            f"{duration:>{duration_width}}  "
            f"({count_text:>{count_width}})"
        )
        lines.append(line)
    # print("\n".join(lines))
    return "\n".join(lines)


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
            SELECT COALESCE(SUM(duration_sec), 0)        AS total_duration_sec,
                   COALESCE(SUM(active_duration_sec), 0) AS total_active_duration_sec,
                   COUNT(*)                              AS session_count
            FROM app_sessions
            WHERE date = ?
            """,
            (day,),
        ).fetchone()

    except sqlite3.Error as exc:
        return empty_status(f'SQLite 错误: {exc}')

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
        # 'Top 应用: ',
    ]

    collector_payload = build_collector_status_payload()

    tooltip_lines.append(fmt_top_apps(top_apps))
    # for idx, row in enumerate(top_apps, start=1):
    #     tooltip_lines.append(
    #         f'{idx}. {row['app_name']} '
    #         f'{fmt_seconds(row['total_active_duration_sec'])} '
    #         f'({row['session_count']} 次)'
    #     )

    tooltip_lines.extend(
        [
            "",
            f"采集状态: {collector_payload['collector_status_label']}",
        ]
    )

    last_action_message = collector_payload.get("last_action_message") or ""
    last_action_time = collector_payload.get("last_action_time") or ""

    if last_action_message:
        if last_action_time:
            tooltip_lines.append(f"最近操作: {last_action_time} {last_action_message}")
        else:
            tooltip_lines.append(f"最近操作: {last_action_message}")

    payload = {
        "active_time": fmt_seconds(total_active_duration_sec),
        "total_time": fmt_seconds(total_duration_sec),
        "top_apps_inline": top_apps_inline,
        "session_count": int(session_count or 0),
        "tooltip": "\n".join(tooltip_lines)
    }

    payload.update(collector_payload)

    return payload


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
