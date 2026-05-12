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