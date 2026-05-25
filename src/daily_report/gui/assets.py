from __future__ import annotations

import os
from pathlib import Path

from daily_report.config.paths import get_installed_share_root


def find_app_icon_path(preferred_size: int = 128) -> Path | None:
    """Find a stable application icon path for Qt window/taskbar usage."""

    env_icon = os.getenv("DAILY_REPORT_APP_ICON")
    sizes = _icon_size_order(preferred_size)
    repo_root = Path(__file__).resolve().parent.parents[2]
    share_root = get_installed_share_root()

    candidates: list[Path] = []
    if env_icon:
        candidates.append(Path(env_icon))

    for size in sizes:
        icon_name = f"icon-{size}.png"
        candidates.extend(
            [
                repo_root / "assets" / "icons" / icon_name,
                share_root / "assets" / "icons" / icon_name,
                repo_root / "frontend" / "src" / "assets" / icon_name,
                share_root / "frontend" / "src" / "assets" / icon_name,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _icon_size_order(preferred_size: int) -> list[int]:
    sizes = [preferred_size, 128, 64, 32]
    return list(dict.fromkeys(sizes))
