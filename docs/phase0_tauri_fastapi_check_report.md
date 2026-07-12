# Phase 0 Tauri + Vue + FastAPI Check Report

## Summary

The repository uses Tauri + Vue + Python FastAPI as its only desktop chain. Python is still run from the local environment and is not bundled through Tauri `externalBin`.

## CLI Entrypoints

Confirmed in `src/daily_report/main.py`:

- `daily-report api`
- `daily-report gui`
- `daily-report gui-tauri`
- `daily-report status --json`
- `daily-report run`
- `daily-report build-prompt`
- `daily-report generate-report`
- `daily-report latest-report`
- `daily-report generate-today` compatibility alias

`daily-report gui` and `daily-report gui-tauri` both launch Tauri.

## Tauri Sidecar

Confirmed in `src-tauri/src/sidecar.rs`, `runtime.rs`, `commands.rs`, and `main.rs`:

- `DAILY_REPORT_TAURI_START_API=1` starts the Python API.
- Host is fixed to `127.0.0.1`.
- `DAILY_REPORT_API_PORT` selects an explicit port; unset or `0` selects a free local port.
- A bearer token is generated per managed startup.
- Runtime config includes `api_base_url`, `api_token`, `api_ready`, `sidecar_mode`, and `last_error`.
- `get_runtime_config`, `check_api_health`, `start_python_api`, and `stop_python_api` are exposed to Vue.
- `stop_python_api` only stops the child process started by Tauri.
- Tauri state `Drop` kills the managed child process on exit.
- `bundle.externalBin` is not configured.

## Vue API Client

Confirmed in `frontend/src/api/client.ts` and `frontend/src/api/runtime.ts`:

- The API client reads `get_runtime_config` and attaches `Authorization: Bearer <token>`.
- If Tauri invoke is unavailable, it falls back to `VITE_API_BASE_URL` and `VITE_API_TOKEN`.
- Browser-only development falls back to `VITE_API_BASE_URL` and still uses HTTP directly.
- Error messages are throttled to avoid repeated toasts.

Vue pages call the FastAPI layer over HTTP. There is no alternate desktop bridge.

## FastAPI

Confirmed in `src/daily_report/api`:

- `create_app(api_token=None)` creates the app.
- `/api/health` and `/api/health/collectors` are unprotected.
- Business routers are protected by bearer token when configured.
- Tokenless local development is allowed when no token is configured.
- CORS is restricted to localhost, 127.0.0.1, and `tauri://localhost`.
- Server defaults to `127.0.0.1`.
- `0.0.0.0` is refused. This was cleaned up to exit without a traceback.
- API responses use the unified `ok/error/code` envelope.

## Data and Service Layer

Confirmed schema tables:

- `app_sessions`
- `app_categories`
- `app_profiles`
- `clipboard_entries`
- `browser_history_entries`
- `ai_prompt_entries`
- `daily_reports`
- `collector_state`
- `entry_annotations`

`init_database` keeps WAL, busy timeout, idempotent schema setup, and safe migrations.

Phase 0 issue found and fixed:

- `daily-report status --json` could fail on Windows GBK stdout because emoji status icons could not be encoded. JSON output now uses ASCII escaping, so stdout remains valid machine-readable JSON.
- `daily-report api --host 0.0.0.0` refused startup but printed a traceback. It now prints a clean error and exits with code 1.

## Edge Extension and YASB

- `edge_extension` remains focused on ChatGPT / DeepSeek prompt capture.
- YASB status remains independent of Tauri, FastAPI, and model calls.
- `status --json` now writes JSON-only stdout successfully.

## Phase 0 Blockers

No remaining blocking Phase 0 issues were found in the checked paths. GUI launch was not kept running interactively during this pass; Tauri was validated with `cargo check`, frontend build, launcher tests, and FastAPI smoke tests.
