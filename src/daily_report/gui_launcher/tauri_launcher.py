from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT_ERROR = (
    "Cannot locate Daily Report project root. Please run this command from the repository "
    "root or set DAILY_REPORT_PROJECT_ROOT."
)

TAURI_FAILURE_HINT = """Tauri GUI failed to start. You can try:
1. Confirm Node.js, npm, Rust, and the Visual Studio C++ build tools are installed.
2. Run npm install in the repository root.
3. Run npm run tauri:dev:sidecar manually."""


def launch_tauri_gui(project_root: Path | None = None, *, manual_api: bool = False) -> int:
    root = locate_project_root(project_root)
    validate_tauri_project(root)
    npm = find_npm()
    script = "tauri:dev" if manual_api else "tauri:dev:sidecar"

    try:
        completed = subprocess.run([npm, "run", script], cwd=root, check=False)
    except OSError as exc:
        print(TAURI_FAILURE_HINT, file=sys.stderr)
        print(f"Underlying error: {exc}", file=sys.stderr)
        return 1

    if completed.returncode != 0:
        print(TAURI_FAILURE_HINT, file=sys.stderr)
    return int(completed.returncode)


def locate_project_root(project_root: Path | None = None) -> Path:
    if project_root is not None:
        root = project_root.expanduser().resolve()
        if is_project_root(root):
            return root
        raise RuntimeError(f"{PROJECT_ROOT_ERROR}\nInvalid --project-root: {root}")

    env_root = os.environ.get("DAILY_REPORT_PROJECT_ROOT")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if is_project_root(root):
            return root
        raise RuntimeError(f"{PROJECT_ROOT_ERROR}\nInvalid DAILY_REPORT_PROJECT_ROOT: {root}")

    search_starts = [Path.cwd(), Path(__file__).resolve()]
    for start in search_starts:
        for candidate in [start, *start.parents]:
            if is_project_root(candidate):
                return candidate

    raise RuntimeError(PROJECT_ROOT_ERROR)


def validate_tauri_project(project_root: Path) -> None:
    if not (project_root / "package.json").exists():
        raise RuntimeError("package.json not found. Please run this command from the repository root.")
    if not (project_root / "src-tauri").exists():
        raise RuntimeError("src-tauri not found. Please complete Tauri migration Phase 3/4 first.")
    if not (project_root / "node_modules").exists():
        raise RuntimeError("node_modules not found. Please run npm install in the repository root.")
    if not (project_root / "frontend" / "node_modules").exists():
        raise RuntimeError(
            "frontend/node_modules not found. Please run npm install in the repository root "
            "or frontend directory."
        )


def find_npm() -> str:
    names = ["npm.cmd", "npm"] if os.name == "nt" else ["npm"]
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("Cannot find npm. Please install Node.js and make sure npm is available in PATH.")


def is_project_root(path: Path) -> bool:
    return (path / "package.json").exists() and (path / "src-tauri").exists()
