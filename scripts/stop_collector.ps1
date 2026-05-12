$ErrorActionPreference = "Continue"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $ProjectRoot "logs"

if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$StopLog = Join-Path $LogDir "collector_stop.log"

function Write-StopLog {
    param([string]$Message)

    Add-Content -Encoding UTF8 $StopLog (
        "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    )
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

foreach ($proc in $rootProcesses) {
    $procId = [int]$proc.ProcessId

    $exists = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue

    if ($null -eq $exists) {
        Write-Host "collector process already exited: $procId"
        Write-StopLog "collector already exited, pid=$procId"
        continue
    }

    try {
        $output = & taskkill.exe /PID $procId /F /T 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            Write-Host "stopped collector process tree: $procId"
            Write-StopLog "collector stopped, root_pid=$procId"
        }
        else {
            Write-Host "failed to stop collector process tree: $procId"
            Write-Host $output
            Write-StopLog "failed to stop collector, root_pid=$procId, output=$output"
        }
    }
    catch {
        Write-Host "failed to stop collector process tree: $procId"
        Write-StopLog "failed to stop collector, root_pid=$procId, error=$($_.Exception.Message)"
    }
}