@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

REM 当前脚本目录，例如 D:\...\daily_report\scripts\
set "SCRIPT_DIR=%~dp0"

REM 项目根目录 = scripts 的上一级
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

set "DAILY_REPORT_EXE=%PROJECT_ROOT%\.venv\Scripts\daily-report.exe"
set "LOG_DIR=%PROJECT_ROOT%\logs"

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$exe = $env:DAILY_REPORT_EXE;" ^
  "$root = $env:PROJECT_ROOT;" ^
  "$logDir = $env:LOG_DIR;" ^
  "$startLog = Join-Path $logDir 'collector_start.log';" ^
  "$stdoutLog = Join-Path $logDir 'collector_stdout.log';" ^
  "$stderrLog = Join-Path $logDir 'collector_stderr.log';" ^
  "if (!(Test-Path $exe)) {" ^
  "  Add-Content -Encoding UTF8 $startLog ('{0} daily-report.exe not found: {1}' -f (Get-Date), $exe);" ^
  "  exit 1;" ^
  "}" ^
  "$running = Get-CimInstance Win32_Process | Where-Object {" ^
  "  $_.CommandLine -and (" ^
  "    (($_.CommandLine.IndexOf($exe, [StringComparison]::OrdinalIgnoreCase) -ge 0) -and ($_.CommandLine -match '(^|[ \t])run([ \t]|$)')) -or" ^
  "    (($_.CommandLine.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0) -and ($_.CommandLine -match 'daily_report\.main|src[\\/]daily_report[\\/]main\.py') -and ($_.CommandLine -match '(^|[ \t])run([ \t]|$)'))" ^
  "  )" ^
  "};" ^
  "if ($running) {" ^
  "  $pids = ($running | Select-Object -ExpandProperty ProcessId) -join ',';" ^
  "  Add-Content -Encoding UTF8 $startLog ('{0} collector already running, pid={1}' -f (Get-Date), $pids);" ^
  "  exit 0;" ^
  "}" ^
  "$p = Start-Process -FilePath $exe -ArgumentList 'run' -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog;" ^
  "Add-Content -Encoding UTF8 $startLog ('{0} collector started, pid={1}' -f (Get-Date), $p.Id);" ^
  "exit 0;"

endlocal