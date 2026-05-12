from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path


def fmt_seconds(sec: int | float | None) -> str:
    sec = int(sec or 0)
    h, rem = divmod(sec, 3600)
    m, _ = divmod(rem, 60)
    if h > 0:
        return f'{h}h{m:02d}m'
    return f'{m}m'


def empty_payload(message: str) -> dict:
    return {
        'active_time': '0m',
        'total_time': '0m',
        'top_apps_inline': message,
        'session_count': 0,
        'tooltip': message,
    }


def main() -> None:
    try:
        from daily_report.storage.database import default_db_path
        db_path = Path(default_db_path())
    except Exception:
        db_path = Path(__file__).resolve().parents[1] / 'data' / 'daily_report.db'

    if not db_path.exists():
        print(json.dumps(empty_payload('数据库尚未创建'), ensure_ascii=False))
        return

    today = date.today().isoformat()

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        total = conn.execute(
            """
            SELECT
                COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
                COALESCE(SUM(active_duration_sec), 0) AS total_active_duration_sec,
                COUNT(*) AS session_count
            FROM app_sessions
            WHERE date = ?
            """,
            (today,),
        ).fetchone()

        rows = conn.execute(
            """
            SELECT
                app_name,
                process_name,
                COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
                COALESCE(SUM(active_duration_sec), 0) AS total_active_duration_sec,
                COUNT(*) AS session_count
            FROM app_sessions
            WHERE date = ?
            GROUP BY app_name, process_name
            ORDER BY total_active_duration_sec DESC
            LIMIT 5
            """,
            (today,),
        ).fetchall()

    except sqlite3.Error as exc:
        print(json.dumps(empty_payload(f'SQLite 错误: {exc}'), ensure_ascii=False))
        return

    top_apps_inline = ' · '.join(
        f'{row['app_name']} {fmt_seconds(row['total_active_duration_sec'])}'
        for row in rows[:3]
    )

    if not top_apps_inline:
        top_apps_inline = '暂无数据'

    tooltip_lines = [
        f'今日总时长: {fmt_seconds(total['total_duration_sec'])}',
        f'今日活跃: {fmt_seconds(total['total_active_duration_sec'])}',
        'Top 应用: ',
    ]

    tooltip_lines.extend(
        f'{idx}. {row['app_name']} {fmt_seconds(row['total_active_duration_sec'])}'
        for idx, row in enumerate(rows, start=1)
    )

    payload = {
        'active_time': fmt_seconds(total['total_active_duration_sec']),
        'total_time': fmt_seconds(total['total_duration_sec']),
        'top_apps_inline': top_apps_inline,
        'session_count': int(total['session_count'] or 0),
        'tooltip': '\n'.join(tooltip_lines),
    }

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()