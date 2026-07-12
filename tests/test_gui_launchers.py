from __future__ import annotations

import subprocess
from pathlib import Path

from daily_report.gui_launcher import tauri_launcher
from daily_report.main import build_parser


def make_tauri_project(root: Path) -> None:
    (root / "src-tauri").mkdir()
    (root / "frontend" / "node_modules").mkdir(parents=True)
    (root / "node_modules").mkdir()
    (root / "package.json").write_text("{}", encoding="utf-8")


def test_locate_project_root_uses_explicit_path(tmp_path):
    make_tauri_project(tmp_path)

    assert tauri_launcher.locate_project_root(tmp_path) == tmp_path.resolve()


def test_locate_project_root_uses_environment(tmp_path, monkeypatch):
    make_tauri_project(tmp_path)
    monkeypatch.setenv("DAILY_REPORT_PROJECT_ROOT", str(tmp_path))

    assert tauri_launcher.locate_project_root() == tmp_path.resolve()


def test_launch_tauri_gui_uses_managed_sidecar_script(tmp_path, monkeypatch):
    make_tauri_project(tmp_path)
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command, cwd, check):
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(tauri_launcher, "find_npm", lambda: "npm.cmd")
    monkeypatch.setattr(tauri_launcher.subprocess, "run", fake_run)

    assert tauri_launcher.launch_tauri_gui(tmp_path) == 0
    assert calls == [(["npm.cmd", "run", "tauri:dev:sidecar"], tmp_path.resolve())]


def test_launch_tauri_gui_manual_api_uses_plain_tauri_dev(tmp_path, monkeypatch):
    make_tauri_project(tmp_path)
    calls: list[list[str]] = []

    def fake_run(command, cwd, check):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(tauri_launcher, "find_npm", lambda: "npm.cmd")
    monkeypatch.setattr(tauri_launcher.subprocess, "run", fake_run)

    assert tauri_launcher.launch_tauri_gui(tmp_path, manual_api=True) == 0
    assert calls == [["npm.cmd", "run", "tauri:dev"]]


def test_cli_gui_defaults_to_tauri_backend():
    args = build_parser().parse_args(["gui"])

    assert args.command == "gui"
    assert not args.manual_api
    assert not args.no_sidecar


def test_cli_generate_today_alias_is_available():
    args = build_parser().parse_args(["generate-today", "--date", "2026-06-01", "--no-save"])

    assert args.command == "generate-today"
    assert args.date == "2026-06-01"
    assert args.no_save
