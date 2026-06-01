use std::env;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use crate::runtime::{AppState, HealthCheckResult, StopResult};

const HOST: &str = "127.0.0.1";
const DEFAULT_PORT: u16 = 8765;

pub fn should_start_python_api() -> bool {
    env::var("DAILY_REPORT_TAURI_START_API")
        .map(|value| value == "1" || value.eq_ignore_ascii_case("true"))
        .unwrap_or(false)
}

pub fn start_python_api(state: &AppState) -> Result<(), String> {
    if has_running_child(state) {
        return Ok(());
    }

    let project_root = resolve_project_root();
    let port = resolve_api_port()?;
    let token = generate_token()?;
    let api_base_url = format!("http://{HOST}:{port}");
    let mut command = build_python_api_command(&project_root, port, &token)?;

    command
        .current_dir(&project_root)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());

    let child = command
        .spawn()
        .map_err(|error| format!("failed to start Python API: {error}"))?;

    {
        let mut process = state
            .python_api
            .lock()
            .map_err(|_| "python process state mutex poisoned".to_string())?;
        process.child = Some(child);
        process.started_by_tauri = true;
    }

    state.update_runtime(|runtime| {
        runtime.api_base_url = api_base_url.clone();
        runtime.api_token = Some(token.clone());
        runtime.api_ready = false;
        runtime.sidecar_mode = "managed".to_string();
        runtime.last_error = None;
    });

    match wait_for_health(&api_base_url, Some(&token), Duration::from_secs(10)) {
        Ok(result) => {
            state.update_runtime(|runtime| {
                runtime.api_ready = result.ok;
                runtime.last_error = result.error.clone();
            });
            Ok(())
        }
        Err(error) => {
            state.set_runtime_error(error.clone());
            Err(error)
        }
    }
}

pub fn stop_python_api(state: &AppState) -> StopResult {
    let mut process = match state.python_api.lock() {
        Ok(process) => process,
        Err(_) => {
            return StopResult {
                stopped: false,
                message: "python process state mutex poisoned".to_string(),
            };
        }
    };

    if !process.started_by_tauri {
        return StopResult {
            stopped: false,
            message: "Python API was not started by Tauri".to_string(),
        };
    }

    let Some(mut child) = process.child.take() else {
        process.started_by_tauri = false;
        state.update_runtime(|runtime| {
            runtime.api_ready = false;
            runtime.api_token = None;
            runtime.sidecar_mode = "manual".to_string();
        });
        return StopResult {
            stopped: false,
            message: "No managed Python API process is running".to_string(),
        };
    };

    let result = child.kill().and_then(|_| child.wait());
    process.started_by_tauri = false;
    state.update_runtime(|runtime| {
        runtime.api_ready = false;
        runtime.api_token = None;
        runtime.sidecar_mode = "manual".to_string();
    });

    match result {
        Ok(_) => StopResult {
            stopped: true,
            message: "Managed Python API process stopped".to_string(),
        },
        Err(error) => StopResult {
            stopped: false,
            message: format!("Failed to stop managed Python API process: {error}"),
        },
    }
}

pub fn check_current_api_health(state: &AppState) -> HealthCheckResult {
    let runtime = state.runtime_config();
    let result = check_api_health(&runtime.api_base_url, runtime.api_token.as_deref());
    state.update_runtime(|runtime| {
        runtime.api_ready = result.ok;
        runtime.last_error = result.error.clone();
    });
    result
}

fn has_running_child(state: &AppState) -> bool {
    let Ok(mut process) = state.python_api.lock() else {
        return false;
    };
    let Some(child) = process.child.as_mut() else {
        return false;
    };
    match child.try_wait() {
        Ok(Some(_status)) => {
            process.child = None;
            process.started_by_tauri = false;
            false
        }
        Ok(None) => true,
        Err(_) => true,
    }
}

fn resolve_api_port() -> Result<u16, String> {
    if let Ok(raw_port) = env::var("DAILY_REPORT_API_PORT") {
        let port = raw_port
            .parse::<u16>()
            .map_err(|_| "DAILY_REPORT_API_PORT must be a valid TCP port".to_string())?;
        if port == 0 {
            return choose_free_port();
        }
        return Ok(port);
    }
    choose_free_port()
}

fn choose_free_port() -> Result<u16, String> {
    let listener = TcpListener::bind((HOST, 0))
        .map_err(|error| format!("failed to reserve a local API port: {error}"))?;
    let port = listener
        .local_addr()
        .map_err(|error| format!("failed to inspect local API port: {error}"))?
        .port();
    drop(listener);
    Ok(port)
}

fn generate_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    getrandom::getrandom(&mut bytes).map_err(|error| format!("failed to generate API token: {error}"))?;
    Ok(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}

fn build_python_api_command(project_root: &Path, port: u16, token: &str) -> Result<Command, String> {
    if let Ok(template) = env::var("DAILY_REPORT_API_COMMAND") {
        let rendered = template
            .replace("{host}", HOST)
            .replace("{port}", &port.to_string())
            .replace("{token}", token);

        #[cfg(windows)]
        {
            let mut command = Command::new("cmd");
            command.args(["/C", &rendered]);
            return Ok(command);
        }

        #[cfg(not(windows))]
        {
            let mut command = Command::new("sh");
            command.args(["-c", &rendered]);
            return Ok(command);
        }
    }

    let python = resolve_python_executable(project_root);
    let mut command = Command::new(python);
    command.args([
        "-m",
        "daily_report.main",
        "api",
        "--host",
        HOST,
        "--port",
        &port.to_string(),
        "--token",
        token,
    ]);
    Ok(command)
}

fn resolve_python_executable(project_root: &Path) -> PathBuf {
    if let Ok(python) = env::var("DAILY_REPORT_PYTHON") {
        if !python.trim().is_empty() {
            return PathBuf::from(python);
        }
    }

    let venv_python = project_root.join(".venv").join("Scripts").join("python.exe");
    if venv_python.exists() {
        return venv_python;
    }

    PathBuf::from("python")
}

fn resolve_project_root() -> PathBuf {
    if let Ok(root) = env::var("DAILY_REPORT_PROJECT_ROOT") {
        if !root.trim().is_empty() {
            return PathBuf::from(root);
        }
    }

    let current_dir = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    if current_dir
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name == "src-tauri")
    {
        return current_dir
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or(current_dir);
    }
    current_dir
}

fn wait_for_health(
    api_base_url: &str,
    token: Option<&str>,
    timeout: Duration,
) -> Result<HealthCheckResult, String> {
    let started_at = Instant::now();
    let mut last_error = None;

    while started_at.elapsed() <= timeout {
        let result = check_api_health(api_base_url, token);
        if result.ok {
            return Ok(result);
        }
        last_error = result.error;
        std::thread::sleep(Duration::from_millis(300));
    }

    Err(last_error.unwrap_or_else(|| "Python API health check timed out".to_string()))
}

fn check_api_health(api_base_url: &str, token: Option<&str>) -> HealthCheckResult {
    let Some((host, port)) = parse_local_base_url(api_base_url) else {
        return HealthCheckResult {
            ok: false,
            status: None,
            error: Some("invalid API base URL".to_string()),
        };
    };

    let address = format!("{host}:{port}");
    let mut stream = match TcpStream::connect_timeout(
        &address.parse().unwrap_or_else(|_| ([127, 0, 0, 1], DEFAULT_PORT).into()),
        Duration::from_millis(500),
    ) {
        Ok(stream) => stream,
        Err(error) => {
            return HealthCheckResult {
                ok: false,
                status: None,
                error: Some(error.to_string()),
            };
        }
    };

    let _ = stream.set_read_timeout(Some(Duration::from_millis(800)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(800)));

    let mut request = format!("GET /api/health HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n");
    if let Some(token) = token {
        request.push_str("Authorization: Bearer ");
        request.push_str(token);
        request.push_str("\r\n");
    }
    request.push_str("\r\n");

    if let Err(error) = stream.write_all(request.as_bytes()) {
        return HealthCheckResult {
            ok: false,
            status: None,
            error: Some(error.to_string()),
        };
    }

    let mut response = String::new();
    if let Err(error) = stream.read_to_string(&mut response) {
        return HealthCheckResult {
            ok: false,
            status: None,
            error: Some(error.to_string()),
        };
    }

    let status = response
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|status| status.parse::<u16>().ok());

    HealthCheckResult {
        ok: status.is_some_and(|status| (200..300).contains(&status)),
        status,
        error: status
            .filter(|status| !(200..300).contains(status))
            .map(|status| format!("health endpoint returned HTTP {status}")),
    }
}

fn parse_local_base_url(api_base_url: &str) -> Option<(String, u16)> {
    let without_scheme = api_base_url
        .strip_prefix("http://")
        .or_else(|| api_base_url.strip_prefix("https://"))?;
    let host_port = without_scheme.split('/').next()?;
    let mut parts = host_port.split(':');
    let host = parts.next()?.to_string();
    let port = parts.next()?.parse::<u16>().ok()?;
    Some((host, port))
}
