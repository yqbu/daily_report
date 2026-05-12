@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set "SCRIPT_DIR=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start_collector.ps1"

endlocal