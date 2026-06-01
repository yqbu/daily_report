mod commands;
mod runtime;
mod sidecar;

use runtime::AppState;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState::new())
        .invoke_handler(tauri::generate_handler![
            commands::get_runtime_config,
            commands::check_api_health,
            commands::start_python_api,
            commands::stop_python_api
        ])
        .setup(|app| {
            let state = app.state::<AppState>();
            if sidecar::should_start_python_api() {
                if let Err(error) = sidecar::start_python_api(&state) {
                    state.set_runtime_error(error);
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to run Daily Report Tauri app");
}

fn main() {
    run();
}
