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
