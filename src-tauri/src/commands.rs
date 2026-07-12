use std::process::Command;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

use tauri::State;

use crate::runtime::{AppState, HealthCheckResult, RuntimeConfig, StopResult};
use crate::sidecar;

#[tauri::command]
pub fn get_runtime_config(state: State<'_, AppState>) -> RuntimeConfig {
    state.runtime_config()
}

#[tauri::command]
pub fn check_api_health(state: State<'_, AppState>) -> HealthCheckResult {
    sidecar::check_current_api_health(&state)
}

#[tauri::command]
pub fn start_python_api(state: State<'_, AppState>) -> Result<RuntimeConfig, String> {
    sidecar::start_python_api(&state)?;
    Ok(state.runtime_config())
}

#[tauri::command]
pub fn stop_python_api(state: State<'_, AppState>) -> StopResult {
    sidecar::stop_python_api(&state)
}

#[derive(Debug, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DirectoryDialogOptions {
    pub title: Option<String>,
    pub current_path: Option<String>,
}

#[derive(Debug, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JsonFileDialogOptions {
    pub title: Option<String>,
    pub current_path: Option<String>,
    pub default_file_name: Option<String>,
}

#[tauri::command]
pub fn select_directory(options: DirectoryDialogOptions) -> Option<String> {
    run_windows_dialog(
        DIRECTORY_DIALOG_SCRIPT,
        &[
            ("DAILY_REPORT_DIALOG_TITLE", options.title),
            ("DAILY_REPORT_DIALOG_PATH", options.current_path),
        ],
    )
}

#[tauri::command]
pub fn select_json_file(options: JsonFileDialogOptions) -> Option<String> {
    run_windows_dialog(
        JSON_FILE_DIALOG_SCRIPT,
        &[
            ("DAILY_REPORT_DIALOG_TITLE", options.title),
            ("DAILY_REPORT_DIALOG_PATH", options.current_path),
            ("DAILY_REPORT_DIALOG_FILE", options.default_file_name),
        ],
    )
}

#[cfg(windows)]
fn run_windows_dialog(script: &str, variables: &[(&str, Option<String>)]) -> Option<String> {
    let mut command = Command::new("powershell.exe");
    command
        .args(["-NoProfile", "-STA", "-Command", script])
        .creation_flags(0x08000000);
    for (name, value) in variables {
        command.env(name, value.as_deref().unwrap_or_default());
    }
    let output = command.output().ok()?;
    if !output.status.success() {
        return None;
    }
    let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
    (!path.is_empty()).then_some(path)
}

#[cfg(not(windows))]
fn run_windows_dialog(_script: &str, _variables: &[(&str, Option<String>)]) -> Option<String> {
    None
}

const DIRECTORY_DIALOG_SCRIPT: &str = r#"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
$dialog = [System.Windows.Forms.FolderBrowserDialog]::new()
$dialog.Description = $env:DAILY_REPORT_DIALOG_TITLE
$dialog.SelectedPath = $env:DAILY_REPORT_DIALOG_PATH
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::Write($dialog.SelectedPath)
}
"#;

const JSON_FILE_DIALOG_SCRIPT: &str = r#"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
$dialog = [System.Windows.Forms.SaveFileDialog]::new()
$dialog.Title = $env:DAILY_REPORT_DIALOG_TITLE
$dialog.Filter = 'JSON files (*.json)|*.json|All files (*.*)|*.*'
$dialog.DefaultExt = 'json'
$dialog.AddExtension = $true
$dialog.FileName = $env:DAILY_REPORT_DIALOG_FILE
$currentPath = $env:DAILY_REPORT_DIALOG_PATH
if ($currentPath) {
    if (Test-Path -LiteralPath $currentPath -PathType Container) {
        $dialog.InitialDirectory = $currentPath
    } else {
        $directory = [System.IO.Path]::GetDirectoryName($currentPath)
        if ($directory) { $dialog.InitialDirectory = $directory }
    }
}
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::Write($dialog.FileName)
}
"#;
