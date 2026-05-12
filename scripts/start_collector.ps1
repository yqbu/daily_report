$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DailyReportExe = Join-Path $ProjectRoot ".venv\Scripts\daily-report.exe"
$LogDir = Join-Path $ProjectRoot "logs"

if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$StartLog = Join-Path $LogDir "collector_start.log"
$StdoutLog = Join-Path $LogDir "collector_stdout.log"
$StderrLog = Join-Path $LogDir "collector_stderr.log"

# 新增：通知脚本路径
$NotifyScript = Join-Path $PSScriptRoot "show_notification.ps1"

$SetStateScript = Join-Path $PSScriptRoot "set_collector_state.ps1"

function Write-StartLog {
    param([string]$Message)

    Add-Content -Encoding UTF8 $StartLog (
        "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    )
}

# 新增：统一通知函数
function Show-CollectorNotification {
    param(
        [string]$Title,
        [string]$Message
    )

    if (!(Test-Path $NotifyScript)) {
        return
    }

    powershell -NoProfile -ExecutionPolicy Bypass -File $NotifyScript `
        -Title $Title `
        -Message $Message `
        -TimeoutMs 3000
}

function Set-CollectorState {
    param(
        [string]$Status,
        [string]$Message,
        [string]$Pids = ""
    )

    if (!(Test-Path $SetStateScript)) {
        return
    }

    powershell -NoProfile -ExecutionPolicy Bypass -File $SetStateScript `
        -Status $Status `
        -Message $Message `
        -Pids $Pids
}

function Test-IsCollectorProcess {
    param($ProcessInfo)

    if ($null -eq $ProcessInfo) {
        return $false
    }

    $cmd = $ProcessInfo.CommandLine

    if ([string]::IsNullOrWhiteSpace($cmd)) {
        return $false
    }

    $inProject = $cmd.IndexOf(
        $ProjectRoot.Path,
        [StringComparison]::OrdinalIgnoreCase
    ) -ge 0

    $isRunCommand = $cmd -match '(^|[\s"`''])run($|[\s"`''])'

    $isDailyReportCommand =
        ($cmd -match 'daily-report(\.exe|-script\.py)?') -or
        ($cmd -match 'daily_report\.main') -or
        ($cmd -match 'src[\\/]daily_report[\\/]main\.py')

    return $inProject -and $isRunCommand -and $isDailyReportCommand
}

if (!(Test-Path $DailyReportExe)) {
    Write-StartLog "daily-report.exe not found: $DailyReportExe"
    Write-Host "daily-report.exe not found: $DailyReportExe"

    Set-CollectorState `
        -Status "error" `
        -Message "启动失败：未找到 daily-report.exe"

    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "启动失败：未找到 daily-report.exe"

    exit 1
}

$running = @(
    Get-CimInstance Win32_Process |
    Where-Object { Test-IsCollectorProcess $_ } |
    Sort-Object ProcessId -Unique
)

if ($running.Count -gt 0) {
    $pidsText = ($running | Select-Object -ExpandProperty ProcessId) -join ","
    Write-StartLog "collector already running, pid=$pidsText"
    Write-Host "collector already running, pid=$pidsText"

    Set-CollectorState `
        -Status "running" `
        -Message "采集服务已经在运行，PID=$pidsText" `
        -Pids $pidsText

    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "采集服务已经在运行，PID=$pidsText"

    exit 0
}

try {
    $proc = Start-Process `
        -FilePath $DailyReportExe `
        -ArgumentList "run" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog

    Write-StartLog "collector started, pid=$($proc.Id)"
    Write-Host "collector started, pid=$($proc.Id)"

    Set-CollectorState `
        -Status "running" `
        -Message "前台应用采集已启动，PID=$($proc.Id)" `
        -Pids "$($proc.Id)"

    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "前台应用采集已启动，PID=$($proc.Id)"

    exit 0
}
catch {
    Write-StartLog "failed to start collector: $($_.Exception.Message)"
    Write-Host "failed to start collector: $($_.Exception.Message)"

    Set-CollectorState `
        -Status "error" `
        -Message "采集服务启动失败：$($_.Exception.Message)"

    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "采集服务启动失败：$($_.Exception.Message)"

    exit 1
}