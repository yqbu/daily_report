## Introduction
Automatically collect computer usage behavior data, select work items, and generate daily reports.

## Development Setup

```powershell
git clone https://github.com/yqbu/daily_report.git
cd daily_report

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
python -m pip install -e .

daily-report status --json
daily-report run
```

## Recommended environment

- Windows 10 / 11

- python.org Python 3.12 x64

- Using conda-forge Python to run the GUI is not recommended

## First deployment
- Executing the `.\scripts\bootstrap.ps1` script through the PowerShell that has been opened in the project directory; if Python is installed in a special position, run `.\scripts\bootstrap.ps1 -PythonExecutable "D:\Somewhere\Python312\python.exe"`