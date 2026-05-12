param(
    [ValidateSet("running", "stopped", "error")]
    [string]$Status,

    [string]$Message = "",

    [string]$Pids = ""
)

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DataDir = Join-Path $ProjectRoot "data"
$StateFile = Join-Path $DataDir "collector_state.json"

if (!(Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

$state = [ordered]@{
    collector_status = $Status
    last_action_message = $Message
    last_action_time = Get-Date -Format "HH:mm:ss"
    last_action_at = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    action_pids = $Pids
}

$json = $state | ConvertTo-Json -Compress

[System.IO.File]::WriteAllText(
    $StateFile,
    $json,
    [System.Text.UTF8Encoding]::new($false)
)