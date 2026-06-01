# Daily Report

Daily Report is a Windows desktop tool for automatically collecting local computer
usage traces, helping users select work-related items, and generating structured
daily reports.

The project is designed for personal productivity scenarios. It collects local
activity data such as foreground application usage, clipboard text, Edge browser
history, and AI prompt records. The desktop UI lets the user review useful
materials before generating a Markdown daily report with a DeepSeek-compatible
chat model.

## Local API

The first-stage Tauri sidecar preparation adds a local FastAPI boundary without
removing the existing CLI or PySide6 GUI.

Start the API:

```powershell
daily-report api --host 127.0.0.1 --port 8765
```

Use a system-assigned port:

```powershell
daily-report api --host 127.0.0.1 --port 0
```

Require a bearer token for protected APIs:

```powershell
daily-report api --host 127.0.0.1 --port 8765 --token <token>
```

When a token is configured, send:

```http
Authorization: Bearer <token>
```

Health endpoints are available without a token. The API defaults to
`127.0.0.1` and refuses `0.0.0.0`.

Available endpoints:

- `GET /api/health`
- `GET /api/health/collectors`
- `GET /api/overview?date=YYYY-MM-DD`
- `GET /api/timeline?date=YYYY-MM-DD&source_type=all&limit=500&offset=0&order=asc`
- `GET /api/entries/{source_type}`
- `GET /api/entries/{source_type}/{id}`
- `PATCH /api/entries/{source_type}/{id}/selection`
- `PATCH /api/entries/{source_type}/{id}/deleted`
- `POST /api/reports/build-prompt`
- `POST /api/reports/generate`
- `GET /api/reports/latest?date=YYYY-MM-DD`
- `GET /api/settings`
- `PUT /api/settings`

All endpoints return JSON in one of these shapes:

```json
{"ok": true, "data": {}}
```

```json
{"ok": false, "error": "message", "code": "ERROR_CODE"}
```

## Vue API Mode

The Vue frontend uses a unified API client. Copy `frontend/.env.example` when you
need local overrides:

```env
# mock | http | qwebchannel | tauri
VITE_API_MODE=http
VITE_API_BASE_URL=http://127.0.0.1:8765
VITE_API_TOKEN=
```

Development flow:

```powershell
daily-report api --host 127.0.0.1 --port 8765
cd frontend
npm run dev
```

Set `VITE_API_MODE=mock` to work on the UI without the Python API. Set
`VITE_API_MODE=qwebchannel` when running through the existing PySide6
QWebChannel path.

## Tauri Development Preview

The third and fourth migration stages add a Tauri v2 desktop shell for the
existing Vue frontend. Python is still run from the development environment and
is not bundled into Tauri yet.

Install the root JavaScript dependencies once before using the Tauri scripts:

```powershell
npm install
```

### Manual API mode

Start the Python API in one terminal:

```powershell
daily-report api --host 127.0.0.1 --port 8765
```

Start the Tauri shell in another terminal:

```powershell
npm run tauri:dev
```

This mode loads the Vue dev server in a Tauri window and uses the API base URL
from Tauri runtime config, falling back to `VITE_API_BASE_URL`.

### Managed Python API mode

```powershell
npm run tauri:dev:sidecar
```

This mode sets `VITE_API_MODE=tauri` and `DAILY_REPORT_TAURI_START_API=1`.
During Tauri startup, Rust starts a local Python FastAPI process on
`127.0.0.1`, selects a free port unless `DAILY_REPORT_API_PORT` is set,
generates an in-memory bearer token, waits for `/api/health`, and exposes the
runtime API config to Vue.

For Tauri runtime config, use:

```env
VITE_API_MODE=tauri
VITE_API_BASE_URL=http://127.0.0.1:8765
VITE_API_TOKEN=
```

Relevant development environment variables:

- `DAILY_REPORT_TAURI_START_API=1`: start Python API from Tauri.
- `DAILY_REPORT_PROJECT_ROOT=`: override the project root used as Python cwd.
- `DAILY_REPORT_PYTHON=`: override the Python executable.
- `DAILY_REPORT_API_COMMAND=`: override the full Python API command template.
  The template may use `{host}`, `{port}`, and `{token}`.
- `DAILY_REPORT_API_PORT=`: force a port; unset to auto-select a free local port.
- `VITE_API_MODE=tauri`: ask Vue to read API config from Tauri commands.

Tauri exposes these commands to the frontend:

- `get_runtime_config`
- `check_api_health`
- `start_python_api`
- `stop_python_api`

This phase intentionally does not configure `bundle.externalBin`, PyInstaller,
Nuitka, cx_Freeze, installers, or auto-update. Packaging the Python sidecar is
left for a later phase.
