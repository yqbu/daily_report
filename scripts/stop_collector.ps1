$ErrorActionPreference = "Continue"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $ProjectRoot "logs"

if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$StopLog = Join-Path $LogDir "collector_stop.log"

# 新增：通知脚本路径
$NotifyScript = Join-Path $PSScriptRoot "show_notification.ps1"

$SetStateScript = Join-Path $PSScriptRoot "set_collector_state.ps1"

function Write-StopLog {
    param([string]$Message)

    Add-Content -Encoding UTF8 $StopLog (
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

    powershell -STA -NoProfile -ExecutionPolicy Bypass -File $NotifyScript `
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

$matched = @(
    Get-CimInstance Win32_Process |
    Where-Object { Test-IsCollectorProcess $_ } |
    Sort-Object ProcessId -Unique
)

if ($matched.Count -eq 0) {
    Write-Host "collector is not running"
    Write-StopLog "collector is not running"

    Set-CollectorState `
        -Status "stopped" `
        -Message "采集服务当前未运行"

    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "采集服务当前未运行"

    exit 0
}

Write-Host "collector processes found:"
$matched | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-Table -AutoSize

$matchedPidSet = @{}
foreach ($proc in $matched) {
    $matchedPidSet[[int]$proc.ProcessId] = $true
}

# 只杀根进程：如果某个进程的父进程也在 matched 里面，
# 那么它会被父进程的 taskkill /T 一起杀掉，不需要重复杀。
$rootProcesses = @(
    $matched |
    Where-Object {
        -not $matchedPidSet.ContainsKey([int]$_.ParentProcessId)
    } |
    Sort-Object ProcessId -Unique
)

if ($rootProcesses.Count -eq 0) {
    # 极端情况下没有识别出根进程，就退回到杀全部，
    # 但每次杀之前仍然检查进程是否存在。
    $rootProcesses = $matched
}

Write-Host ""
Write-Host "collector root processes to stop:"
$rootProcesses | Select-Object ProcessId, ParentProcessId, Name | Format-Table -AutoSize

$stoppedPids = @()
$failedPids = @()
$alreadyExitedPids = @()

foreach ($proc in $rootProcesses) {
    $procId = [int]$proc.ProcessId

    $exists = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue

    if ($null -eq $exists) {
        Write-Host "collector process already exited: $procId"
        Write-StopLog "collector already exited, pid=$procId"
        $alreadyExitedPids += $procId
        continue
    }

    try {
        $output = & taskkill.exe /PID $procId /F /T 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            Write-Host "stopped collector process tree: $procId"
            Write-StopLog "collector stopped, root_pid=$procId"
            $stoppedPids += $procId
        }
        else {
            Write-Host "failed to stop collector process tree: $procId"
            Write-Host $output
            Write-StopLog "failed to stop collector, root_pid=$procId, output=$output"
            $failedPids += $procId
        }
    }
    catch {
        Write-Host "failed to stop collector process tree: $procId"
        Write-StopLog "failed to stop collector, root_pid=$procId, error=$($_.Exception.Message)"
        $failedPids += $procId
    }
}

if ($failedPids.Count -gt 0) {
    $failedText = $failedPids -join ","

    Set-CollectorState `
        -Status "error" `
        -Message "采集服务停止失败，PID=$failedText" `
        -Pids $failedText

    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "采集服务停止失败，PID=$failedText"

    exit 1
}

if ($stoppedPids.Count -gt 0) {
    $stoppedText = $stoppedPids -join ","

    Set-CollectorState `
        -Status "stopped" `
        -Message "采集服务已停止，PID=$stoppedText" `
        -Pids $stoppedText

    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "采集服务已停止，PID=$stoppedText"

    exit 0
}

if ($alreadyExitedPids.Count -gt 0) {
    Set-CollectorState `
        -Status "stopped" `
        -Message "采集服务已经退出"
    Show-CollectorNotification `
        -Title "Daily Report" `
        -Message "采集服务已经退出"

    exit 0
}

Show-CollectorNotification `
    -Title "Daily Report" `
    -Message "未发现需要停止的采集服务"

exit 0