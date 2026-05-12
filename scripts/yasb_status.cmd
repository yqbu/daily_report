@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

REM 获取当前 .cmd 文件所在目录, 例如 D:\...\daily_report\scripts\
set "SCRIPT_DIR=%~dp0"

REM 项目根目录 = scripts 的上一级目录
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

set "DAILY_REPORT_EXE=%PROJECT_ROOT%\.venv\Scripts\daily-report.exe"

if not exist "%DAILY_REPORT_EXE%" (
    echo {"active_time":"ERR","total_time":"ERR","top_apps_inline":"daily-report.exe not found","session_count":0,"tooltip":"daily-report.exe not found: %DAILY_REPORT_EXE%"}
    exit /b 1
)

"%DAILY_REPORT_EXE%" status --json

endlocal