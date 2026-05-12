@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

REM 当前脚本目录，例如 D:\...\daily_report\scripts\
set "SCRIPT_DIR=%~dp0"

REM 项目根目录 = scripts 的上一级
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

set "LOCK_FILE=%PROJECT_ROOT%\data\daily_report_collector.lock"
set "LOG_DIR=%PROJECT_ROOT%\logs"

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'SilentlyContinue';" ^
  "$root = $env:PROJECT_ROOT;" ^
  "$lockFile = $env:LOCK_FILE;" ^
  "$logDir = $env:LOG_DIR;" ^
  "$stopLog = Join-Path $logDir 'collector_stop.log';" ^
  "function Write-StopLog($msg) {" ^
  "  Add-Content -Encoding UTF8 $stopLog ('{0} {1}' -f (Get-Date), $msg);" ^
  "}" ^
  "function Is-CollectorProcess($p) {" ^
  "  if ($null -eq $p -or [string]::IsNullOrWhiteSpace($p.CommandLine)) { return $false }" ^
  "  $cmd = $p.CommandLine;" ^
  "  $inProject = $cmd.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0;" ^
  "  $isRun = $cmd -match '(^|[ \t\"''])(run)([ \t\"'']|$)';" ^
  "  $isDailyReportExe = $cmd -match 'daily-report(\.exe)?';" ^
  "  $isPythonMain = ($cmd -match 'daily_report\.main') -or ($cmd -match 'src[\\/]daily_report[\\/]main\.py');" ^
  "  return $inProject -and $isRun -and ($isDailyReportExe -or $isPythonMain);" ^
  "}" ^
  "$targetPids = @();" ^
  "if (Test-Path $lockFile) {" ^
  "  $lockText = Get-Content $lockFile -Raw;" ^
  "  if ($lockText -match 'pid=(\d+)') {" ^
  "    $pidFromLock = [int]$Matches[1];" ^
  "    $p = Get-CimInstance Win32_Process -Filter ('ProcessId={0}' -f $pidFromLock);" ^
  "    if (Is-CollectorProcess $p) {" ^
  "      $targetPids += $pidFromLock;" ^
  "    } else {" ^
  "      Write-StopLog ('lock pid is stale or not collector, pid={0}' -f $pidFromLock);" ^
  "    }" ^
  "  }" ^
  "}" ^
  "if ($targetPids.Count -eq 0) {" ^
  "  $matched = Get-CimInstance Win32_Process | Where-Object { Is-CollectorProcess $_ };" ^
  "  if ($matched) {" ^
  "    $targetPids += @($matched | Select-Object -ExpandProperty ProcessId);" ^
  "  }" ^
  "}" ^
  "$targetPids = @($targetPids | Sort-Object -Unique);" ^
  "if ($targetPids.Count -eq 0) {" ^
  "  Write-StopLog 'collector is not running';" ^
  "  exit 0;" ^
  "}" ^
  "foreach ($pid in $targetPids) {" ^
  "  try {" ^
  "    Stop-Process -Id $pid -Force;" ^
  "    Write-StopLog ('collector stopped, pid={0}' -f $pid);" ^
  "  } catch {" ^
  "    Write-StopLog ('failed to stop collector, pid={0}, error={1}' -f $pid, $_.Exception.Message);" ^
  "  }" ^
  "}" ^
  "exit 0;"

endlocal