param(
    [string]$Title = "Daily Report",
    [string]$Message = "",
    [int]$TimeoutMs = 3000
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = $Title
$form.Width = 360
$form.Height = 110
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(35, 35, 35)

# 关键：先完全透明，避免创建窗口时白闪
$form.Opacity = 0

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$form.Left = $screen.Right - $form.Width - 20
$form.Top = $screen.Bottom - $form.Height - 20

$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = $Title
$titleLabel.ForeColor = [System.Drawing.Color]::White
$titleLabel.BackColor = $form.BackColor
$titleLabel.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 10, [System.Drawing.FontStyle]::Bold)
$titleLabel.AutoSize = $false
$titleLabel.Left = 16
$titleLabel.Top = 12
$titleLabel.Width = 300
$titleLabel.Height = 24

$messageLabel = New-Object System.Windows.Forms.Label
$messageLabel.Text = $Message
$messageLabel.ForeColor = [System.Drawing.Color]::Gainsboro
$messageLabel.BackColor = $form.BackColor
$messageLabel.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 9)
$messageLabel.AutoSize = $false
$messageLabel.Left = 16
$messageLabel.Top = 42
$messageLabel.Width = 320
$messageLabel.Height = 45

$closeLabel = New-Object System.Windows.Forms.Label
$closeLabel.Text = "×"
$closeLabel.ForeColor = [System.Drawing.Color]::Silver
$closeLabel.BackColor = $form.BackColor
$closeLabel.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 12, [System.Drawing.FontStyle]::Bold)
$closeLabel.AutoSize = $false
$closeLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$closeLabel.Left = 330
$closeLabel.Top = 6
$closeLabel.Width = 20
$closeLabel.Height = 20
$closeLabel.Cursor = [System.Windows.Forms.Cursors]::Hand
$closeLabel.Add_Click({
    $form.Close()
})

$form.Controls.Add($titleLabel)
$form.Controls.Add($messageLabel)
$form.Controls.Add($closeLabel)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = $TimeoutMs
$timer.Add_Tick({
    $timer.Stop()
    $form.Close()
})

$form.Add_Shown({
    # 关键：等窗口和控件都创建完成后再显示
    $form.Refresh()
    Start-Sleep -Milliseconds 30
    $form.Opacity = 0.96
    $form.Activate()
    $timer.Start()
})

[void]$form.ShowDialog()