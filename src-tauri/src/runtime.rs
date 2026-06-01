use std::process::Child;
use std::sync::Mutex;

#[derive(Debug, Clone, serde::Serialize)]
pub struct RuntimeConfig {
    pub api_base_url: String,
    pub api_token: Option<String>,
    pub api_ready: bool,
    pub sidecar_mode: String,
    pub last_error: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct HealthCheckResult {
    pub ok: bool,
    pub status: Option<u16>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct StopResult {
    pub stopped: bool,
    pub message: String,
}

pub struct PythonApiProcess {
    pub child: Option<Child>,
    pub started_by_tauri: bool,
}

pub struct AppState {
    pub runtime: Mutex<RuntimeConfig>,
    pub python_api: Mutex<PythonApiProcess>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            runtime: Mutex::new(RuntimeConfig {
                api_base_url: "http://127.0.0.1:8765".to_string(),
                api_token: None,
                api_ready: false,
                sidecar_mode: "manual".to_string(),
                last_error: None,
            }),
            python_api: Mutex::new(PythonApiProcess {
                child: None,
                started_by_tauri: false,
            }),
        }
    }

    pub fn runtime_config(&self) -> RuntimeConfig {
        self.runtime
            .lock()
            .expect("runtime state mutex poisoned")
            .clone()
    }

    pub fn update_runtime<F>(&self, update: F)
    where
        F: FnOnce(&mut RuntimeConfig),
    {
        let mut runtime = self.runtime.lock().expect("runtime state mutex poisoned");
        update(&mut runtime);
    }

    pub fn set_runtime_error(&self, error: String) {
        self.update_runtime(|runtime| {
            runtime.api_ready = false;
            runtime.last_error = Some(error);
        });
    }
}

impl Drop for AppState {
    fn drop(&mut self) {
        if let Ok(mut process) = self.python_api.lock() {
            if process.started_by_tauri {
                if let Some(mut child) = process.child.take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
                process.started_by_tauri = false;
            }
        }
    }
}
