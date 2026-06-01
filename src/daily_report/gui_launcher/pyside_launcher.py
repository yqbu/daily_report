from __future__ import annotations


def launch_pyside_gui(
    *,
    dev: bool = False,
    dev_port: int = 5173,
    remote_debugging_port: int | None = None,
    manage_api: bool = True,
    api_host: str = "127.0.0.1",
    api_port: int = 8765,
) -> int:
    # Legacy PySide6 GUI entry. Kept as fallback during Tauri migration.
    from daily_report.gui.web_app import run_gui

    return run_gui(
        dev=dev,
        dev_port=dev_port,
        remote_debugging_port=remote_debugging_port,
        manage_api=manage_api,
        api_host=api_host,
        api_port=api_port,
    )

