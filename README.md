# Daily Report

Daily Report is a Windows desktop tool for automatically collecting local computer usage traces, helping users select work-related items, and generating structured daily reports.

The project is designed for personal productivity scenarios. It collects local activity data such as foreground application usage, clipboard text, browser history, and AI prompt records, then allows the user to review and select useful items before generating a Markdown daily report.

## Features

Current and planned features include:

- Foreground application usage collection
- Clipboard text collection
- Edge browser history collection
- ChatGPT / DeepSeek prompt collection through a lightweight browser extension
- Local SQLite storage
- PySide6-based desktop GUI
- Manual selection of report materials
- DeepSeek API-based Markdown daily report generation
- YASB integration for lightweight status display and quick actions

## Recommended Environment

- Windows 10 / 11
- python.org Python 3.12 x64
- PowerShell
- A local virtual environment created by `venv`

Using conda-forge Python to run the GUI is not recommended, especially for PySide6-based desktop interfaces, because Qt-related DLL dependencies may conflict with conda environments.

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

Install the project in editable mode:

```powershell
python -m pip install -U pip
python -m pip install -e .
```

Run the CLI:

```powershell
daily-report status --json
daily-report run
```

## First Deployment

For a fresh Windows environment, it is recommended to use the bootstrap script:

```powershell
.\scripts\bootstrap.ps1
```

The script will:

- Locate a suitable Python 3.11 / 3.12 executable
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

Install or update dependencies:

```powershell
python -m pip install -U pip
python -m pip install -e .
```

If development dependencies are defined in `pyproject.toml`, install them with:

```powershell
python -m pip install -e ".[dev]"
```

## Project Structure

A recommended project structure is:

```text
daily_report/
├─ pyproject.toml
├─ README.md
├─ configs/
│  ├─ app.yaml
│  ├─ model.yaml
│  └─ privacy_rules.yaml
├─ scripts/
│  └─ bootstrap.ps1
├─ edge_extension/
│  ├─ manifest.json
│  ├─ content_script.js
│  └─ background.js
└─ src/
   └─ daily_report/
      ├─ main.py
      ├─ collector/
      ├─ storage/
      ├─ report/
      ├─ gui/
      ├─ service/
      └─ yasb_bridge/
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

Generate today's report:

```powershell
daily-report generate-today
```

## Troubleshooting

### `python` points to WindowsApps

If `where.exe python` shows a path like:

```text
...\Microsoft\WindowsApps\python.exe
```

it may be the Windows Python execution alias rather than a real Python installation.

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

use a clean python.org Python 3.12 virtual environment instead of conda Python:

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

This project is currently under active development. Add a license before public release.