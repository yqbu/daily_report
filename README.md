# Daily Report

Daily Report is a Windows desktop tool for automatically collecting local computer
usage traces, helping users select work-related items, and generating structured
daily reports.

The project is designed for personal productivity scenarios. It collects local
activity data such as foreground application usage, clipboard text, Edge browser
history, and AI prompt records. The desktop UI lets the user review useful
materials before generating a Markdown daily report with a DeepSeek-compatible
chat model.

## Features

- Foreground application usage collection
- Clipboard text collection with sensitive-content detection
- Edge browser history collection
- ChatGPT / DeepSeek prompt collection through a lightweight Edge extension
- Local SQLite storage
- PySide6 + QWebEngine desktop shell with a Vue SPA frontend
- Manual selection of report materials
- OpenAI-compatible DeepSeek report generation
- YASB integration for lightweight status display and quick actions

## Recommended Environment

- Windows 10 / 11
- python.org Python 3.12 x64
- PowerShell
- Node.js and npm for the Vue frontend
- A local virtual environment created by `venv`

Using conda-forge Python to run the GUI is not recommended, especially for
PySide6-based desktop interfaces, because Qt-related DLL dependencies may
conflict with conda environments.

## Quick Start

Clone the project:

```powershell
git clone https://github.com/yqbu/daily_report.git
cd daily_report
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the Python package in editable mode:

```powershell
python -m pip install -U pip
python -m pip install -e .
```

Build the web UI:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Run the CLI:

```powershell
daily-report status --json
daily-report run
daily-report gui
```

## First Deployment

For a fresh Windows environment, it is recommended to use the bootstrap script:

```powershell
.\scripts\bootstrap.ps1
```

The script will:

- Locate a suitable Python executable
- Skip WindowsApps placeholder Python executables
- Avoid conda Python by default
- Create a `.venv` virtual environment
- Install project dependencies from `pyproject.toml`
- Test whether PySide6 can be imported successfully

If Python is installed in a non-standard location, specify it explicitly:

```powershell
.\scripts\bootstrap.ps1 -PythonExecutable "D:\Somewhere\Python312\python.exe"
```

To recreate the virtual environment from scratch:

```powershell
.\scripts\bootstrap.ps1 -Force
```

To install development dependencies:

```powershell
.\scripts\bootstrap.ps1 -Dev
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then execute the bootstrap script again.

## Development Setup

After the first deployment, activate the virtual environment before development:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install or update the runtime dependencies:

```powershell
python -m pip install -U pip
python -m pip install -e .
```

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run basic checks:

```powershell
ruff check .
```

### Web GUI Development

The desktop GUI uses one `QWebEngineView` to host the Vue SPA. The Python side
exposes data through `QWebChannel`; collector, storage, report, service, and
YASB modules remain Python-owned.

Build production assets before launching the desktop UI:

```powershell
cd frontend
npm install
npm run build
cd ..
daily-report gui
```

For frontend development, start Vite and point the desktop shell at the dev
server:

```powershell
cd frontend
npm run dev
```

In another terminal:

```powershell
$env:DAILY_REPORT_WEB_DEV_SERVER = "http://127.0.0.1:5173"
daily-report gui
```

Or use one command to start both Vite and the desktop shell:

```powershell
daily-report gui --dev --remote-debugging
```

This starts `npm run dev` in `frontend/`, waits for
`http://127.0.0.1:5173`, then opens the QWebEngine window with real Python
Bridge access. Closing the desktop window stops the Vite process started by
this command.

To inspect the Web UI inside QWebEngine with browser DevTools:

```powershell
$env:DAILY_REPORT_WEB_DEV_SERVER = "http://127.0.0.1:5173"
$env:QTWEBENGINE_REMOTE_DEBUGGING = "9223"
daily-report gui
```

Then open `http://127.0.0.1:9223` in Chrome or Edge and select the Daily
Reporter page. Running `npm run dev` directly in a normal browser is useful
for layout work, but Python Bridge calls only use real data inside the
QWebEngine desktop shell; browser-only mode falls back to mock or empty
responses.

If `frontend/dist/index.html` does not exist and no dev server URL is
configured, the desktop window shows a build instruction page instead of
failing silently.

## Project Structure

```text
daily_report/
|-- pyproject.toml
|-- README.md
|-- configs/
|   `-- app.yaml
|-- scripts/
|   |-- bootstrap.ps1
|   |-- start_collector.ps1
|   |-- stop_collector.ps1
|   `-- yasb_status.cmd
|-- edge_extension/
|   |-- manifest.json
|   |-- content_script.js
|   `-- README.md
|-- frontend/
|   |-- package.json
|   |-- src/
|   `-- vite.config.ts
`-- src/
    `-- daily_report/
        |-- main.py
        |-- collector/
        |-- config/
        |-- gui/
        |-- reporter/
        |-- service/
        |-- storage/
        `-- yasb_bridge/
```

## Common Commands

Show current status as JSON:

```powershell
daily-report status --json
```

Run the collector service:

```powershell
daily-report run
```

Open the GUI:

```powershell
daily-report gui
```

Build a report prompt without calling the model:

```powershell
daily-report build-prompt --date 2026-05-18 --out output\prompt.txt
```

Generate and save a report:

```powershell
daily-report generate-report --date 2026-05-18 --out output\daily-report.md
```

Print the latest saved report for a date:

```powershell
daily-report latest-report --date 2026-05-18
```

## Troubleshooting

### `python` points to WindowsApps

If `where.exe python` shows a path like:

```text
...\Microsoft\WindowsApps\python.exe
```

it may be the Windows Python execution alias rather than a real Python
installation.

Open the app execution alias settings:

```powershell
start ms-settings:appsfeatures-appaliases
```

Then disable:

- `python.exe`
- `python3.exe`

After that, reopen PowerShell and check again:

```powershell
where.exe python
python --version
```

### PySide6 fails to import QtCore

If you see an error similar to:

```text
ImportError: DLL load failed while importing QtCore
```

use a clean python.org Python 3.12 virtual environment instead of conda
Python:

```powershell
.\scripts\bootstrap.ps1 -Force
```

If Python is installed in a custom location:

```powershell
.\scripts\bootstrap.ps1 -PythonExecutable "D:\Somewhere\Python312\python.exe" -Force
```

### Conda automatically activates base

Disable automatic activation of the base environment:

```powershell
conda config --set auto_activate_base false
```

Then close and reopen the terminal.

## Privacy Notes

Daily Report is designed as a local-first tool.

- Collected data is stored locally by default.
- Clipboard content should be filtered and previewed before use.
- Sensitive content should not be selected automatically.
- Data should be manually reviewed before being sent to any model API.
- AI report generation should use only user-selected materials.

## License

This project is currently under active development. Add a license before public
release.
