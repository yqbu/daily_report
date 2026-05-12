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

function Write-StartLog {
    param([string]$Message)

    Add-Content -Encoding UTF8 $StartLog (
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

if (!(Test-Path $DailyReportExe)) {
    Write-StartLog "daily-report.exe not found: $DailyReportExe"
    Write-Host "daily-report.exe not found: $DailyReportExe"
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
    exit 0
}
catch {
    Write-StartLog "failed to start collector: $($_.Exception.Message)"
    Write-Host "failed to start collector: $($_.Exception.Message)"
    exit 1
}