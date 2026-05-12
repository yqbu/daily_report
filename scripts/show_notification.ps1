param(
    [string]$Title = "Daily Report",
    [string]$Message = "",
    [int]$TimeoutMs = 3000
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = $Title
$notify.BalloonTipText = $Message
$notify.Visible = $true

$notify.ShowBalloonTip($TimeoutMs)

Start-Sleep -Milliseconds ($TimeoutMs + 500)

$notify.Dispose()