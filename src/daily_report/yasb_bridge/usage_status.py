from __future__ import annotations

import json
from datetime import date as date_cls
from typing import Any

from daily_report.service.overview_service import OverviewService


def fmt_seconds(sec: int | float | None) -> str:
    seconds = int(sec or 0)
    hours, rem = divmod(seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f'{hours}h{minutes:02d}m'
    return f'{minutes}m'


def fmt_top_apps(apps: list[dict[str, Any]], with_header: bool = True) -> str:
    if not apps:
        return 'No app usage data.'

    rank_width = max(len('No.'), len(f'{len(apps)}.'))
    name_width = max(len('Top App'), max(len(item['app_name']) for item in apps))
    duration_width = max(len('Time'), max(len(fmt_seconds(item['seconds'])) for item in apps))
    count_texts = [f"{item['session_count']} 次" for item in apps]
    count_width = max(len('Count'), max(len(text) for text in count_texts))

    lines = []

    if with_header:
        header = (
            f"{'No.':<{rank_width}} "
            f"{'Top App':<{name_width}} "
            f"{'Time':>{duration_width}} "
            f"{'Count':>{count_width}}"
        )
        lines.append(header)
        lines.append('-' * (len(header) + 2))

    for idx, item in enumerate(apps, start=1):
        line = (
            f'{str(idx) + ".":<{rank_width}} '
            f'{item["app_name"]:<{name_width}} '
            f'{fmt_seconds(item["seconds"]):>{duration_width}} '
            f'({count_texts[idx - 1]:>{count_width}})'
        )
        lines.append(line)

    return '\n'.join(lines)


def build_status_payload(
        *,
        target_date: str | None = None,
        limit: int = 5,
) -> dict[str, Any]:
    day = target_date or date_cls.today().isoformat()
    try:
        overview = OverviewService().get_overview(day)
    except Exception as exc:
        return _empty_status(day, f'状态读取失败: {exc}')

    top_apps = list(overview.get('top_apps') or [])[:limit]
    top_apps_inline = ' · '.join(
        f"{app.get('name') or app.get('app_name')} {fmt_seconds(app.get('seconds'))}"
        for app in top_apps
        if app.get('name') or app.get('app_name')
    ) or '暂无数据'

    tooltip = '\n'.join(
        [
            f"日期: {day}",
            f"今日活跃/总时长: {overview.get('active_time', '0m')} / {overview.get('total_time', '0m')}",
            # f"Top应用: {top_apps_inline}",
            f"{fmt_top_apps(top_apps)}",
            (
                "数据源: "
                f"前台 {overview.get('app_session_count', 0)} / "
                f"浏览 {overview.get('browser_count', 0)} / "
                f"浏览器事件 {overview.get('browser_event_count', 0)} / "
                f"剪切板 {overview.get('clipboard_count', 0)} / "
                f"AI {overview.get('ai_prompt_count', 0)}"
            ),
            # f"已选素材: {overview.get('selected_material_count', 0)}",
            # f"敏感记录: {overview.get('sensitive_count', 0)}",
            f"日报状态: {overview.get('report_status', '未生成')}",
            f"采集状态: {overview.get('collector_status_label') or overview.get('collector_status', 'unknown')}",
        ]
    )

    return {
        'date': day,
        'collector_status': overview.get('collector_status', 'unknown'),
        'collector_status_label': overview.get('collector_status_label', '未知'),
        'collector_status_icon': overview.get('collector_status_icon', '❓'),
        'active_time': overview.get('active_time', '0m'),
        'total_time': overview.get('total_time', '0m'),
        'top_apps_inline': top_apps_inline,
        'app_session_count': int(overview.get('app_session_count') or 0),
        'browser_count': int(overview.get('browser_count') or 0),
        'browser_event_count': int(overview.get('browser_event_count') or 0),
        'clipboard_count': int(overview.get('clipboard_count') or 0),
        'ai_prompt_count': int(overview.get('ai_prompt_count') or 0),
        'selected_material_count': int(overview.get('selected_material_count') or 0),
        'sensitive_count': int(overview.get('sensitive_count') or 0),
        'report_status': overview.get('report_status', '未生成'),
        'collector_states': overview.get('collector_states', []),
        'tooltip': tooltip,
    }


def print_status(
        *,
        target_date: str | None = None,
        limit: int = 5,
        as_json: bool = True,
) -> None:
    payload = build_status_payload(target_date=target_date, limit=limit)
    if as_json:
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print(payload['tooltip'])


def _empty_status(day: str, message: str) -> dict[str, Any]:
    return {
        'date': day,
        'collector_status': 'unknown',
        'collector_status_label': '未知',
        'collector_status_icon': '❓',
        'active_time': '0m',
        'total_time': '0m',
        'top_apps_inline': '暂无数据',
        'app_session_count': 0,
        'browser_count': 0,
        'browser_event_count': 0,
        'clipboard_count': 0,
        'ai_prompt_count': 0,
        'selected_material_count': 0,
        'sensitive_count': 0,
        'report_status': '未生成',
        'tooltip': message,
    }
