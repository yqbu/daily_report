from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import psutil

from daily_report.storage.database import default_db_path


def get_project_root() -> Path:
    return Path(default_db_path()).resolve().parent.parent


def get_collector_state_path() -> Path:
    return Path(default_db_path()).resolve().parent / "collector_state.json"


def read_collector_action_state() -> dict[str, Any]:
    state_path = get_collector_state_path()

    default_state = {
        "collector_status": "unknown",
        "last_action_message": "",
        "last_action_time": "",
        "last_action_at": "",
        "action_pids": "",
    }

    if not state_path.exists():
        return default_state

    try:
        data = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default_state

    if not isinstance(data, dict):
        return default_state

    default_state.update(data)
    return default_state


def find_collector_processes() -> list[dict[str, Any]]:
    project_root = str(get_project_root()).lower()
    matched: list[dict[str, Any]] = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            info = proc.info
            cmdline = info.get("cmdline") or []

            if not cmdline:
                continue

            command_line = " ".join(str(part) for part in cmdline)
            command_line_lower = command_line.lower()

            in_project = project_root in command_line_lower
            is_run_command = re.search(
                r"(^|[\s\"'])run($|[\s\"'])",
                command_line,
            ) is not None

            is_daily_report_command = (
                re.search(r"daily-report(\.exe|-script\.py)?", command_line, re.I)
                is not None
                or re.search(r"daily_report\.main", command_line, re.I)
                is not None
                or re.search(r"src[\\/]daily_report[\\/]main\.py", command_line, re.I)
                is not None
            )

            if in_project and is_run_command and is_daily_report_command:
                matched.append(
                    {
                        "pid": int(info["pid"]),
                        "name": info.get("name") or "",
                        "command_line": command_line,
                    }
                )

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    matched.sort(key=lambda item: item["pid"])
    return matched


def build_collector_status_payload() -> dict[str, Any]:
    action_state = read_collector_action_state()
    processes = find_collector_processes()

    is_running = len(processes) > 0

    if is_running:
        collector_status = "running"
        collector_status_label = "采集中"
    else:
        collector_status = "stopped"
        collector_status_label = "未运行"

    pids = ",".join(str(item["pid"]) for item in processes)

    return {
        "collector_status": collector_status,
        "collector_status_label": collector_status_label,
        "collector_pids": pids,
        "collector_process_count": len(processes),
        "last_action_message": action_state.get("last_action_message", ""),
        "last_action_time": action_state.get("last_action_time", ""),
        "last_action_at": action_state.get("last_action_at", ""),
    }