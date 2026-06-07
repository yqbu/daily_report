# Daily Report

Daily Report is a Windows desktop tool for automatically collecting local computer
usage traces, helping users select work-related items, and generating structured
daily reports.

The project is designed for personal productivity scenarios. It collects local
activity data such as foreground application usage, clipboard text, Edge browser
history, lightweight browser behavior events, and AI prompt records. The desktop UI lets the user review useful
materials before generating a Markdown daily report with a DeepSeek-compatible
chat model.

## Migration Status

Current migration phase:

1. Phase 1: Python FastAPI API boundary.
2. Phase 2: Vue frontend reads data through HTTP APIs.
3. Phase 3: Create the Tauri shell without bundling Python.
4. Phase 4: Tauri starts the local Python FastAPI process in development.
5. Phase 5: Tauri is the primary GUI entry, replacing PySide6 for daily use without bundling Python.
6. Phase 6: Package the Python sidecar.
7. Phase 7: Remove or downgrade the PySide6 GUI.

This repository is currently in Phase 5. Python is not bundled, Tauri does not
use `externalBin`, and the app still depends on the local source checkout and
Python environment.

## Recommended GUI Entry

Use the Tauri GUI for daily development and self-use testing:

```powershell
daily-report gui
```

This is equivalent to:

```powershell
npm run tauri:dev:sidecar
```

It starts the Tauri shell and lets Tauri start the local Python FastAPI process
on `127.0.0.1`. Vue reads the runtime API URL and bearer token from Tauri, then
uses HTTP APIs to talk to Python.

Explicit Tauri entry:

```powershell
daily-report gui-tauri
```

Legacy PySide6 fallback:

```powershell
daily-report gui-pyside
```

`daily-report gui --backend pyside` is also accepted as a compatibility path,
but `daily-report gui-pyside` is the clearer legacy command.

PySide6 GUI is kept as a legacy fallback during the Tauri migration. New UI
development should target the Vue + Tauri frontend. PySide6 GUI is temporarily
kept for compatibility; new screens and features should be implemented in
Vue + Tauri first.

Manual API mode is still available:

```powershell
daily-report api --host 127.0.0.1 --port 8765
daily-report gui --manual-api
```

Or:

```powershell
daily-report api --host 127.0.0.1 --port 8765
npm run tauri:dev
```

Current Phase 5 limits:

- Python is not bundled.
- The app depends on the local Python environment, usually `.venv`.
- The app depends on the repository source directory.
- This is not a redistributable installer build.
- Phase 6 will add proper Python sidecar packaging.

## Local API

The Tauri migration uses a local FastAPI boundary without removing the existing
CLI or legacy PySide6 GUI.

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
- `GET /api/extension/health`
- `GET /api/overview?date=YYYY-MM-DD`
- `GET /api/timeline?date=YYYY-MM-DD&source_type=all&record_type=search&limit=500&offset=0&order=asc`
- `GET /api/entries/{source_type}?record_type=search`
- `GET /api/entries/by-key/{entry_key}`
- `PATCH /api/entries/by-key/selection`
- `PATCH /api/entries/by-key/deleted`
- `PATCH /api/entries/by-key/annotation`
- `PATCH /api/entries/by-key/sensitive`
- `GET /api/entries/{source_type}/{id}`
- `PATCH /api/entries/{source_type}/{id}/selection`
- `PATCH /api/entries/{source_type}/{id}/deleted`
- `POST /api/events/browser`
- `POST /api/ai-prompt`
- `POST /api/reports/build-prompt`
- `POST /api/reports/generate`
- `GET /api/reports/latest?date=YYYY-MM-DD`
- `GET /api/runtime/summary`
- `GET /api/runtime/processes`
- `GET /api/runtime/health`
- `POST /api/runtime/doctor`
- `POST /api/runtime/repair`
- `POST /api/runtime/cleanup-orphans`
- `POST /api/runtime/processes/{pid}/terminate`
- `POST /api/runtime/processes/{pid}/kill`
- `POST /api/runtime/collector/start`
- `POST /api/runtime/collector/stop`
- `POST /api/runtime/collector/restart`
- `GET /api/settings`
- `PUT /api/settings`

All endpoints return JSON in one of these shapes:

```json
{"ok": true, "data": {}}
```

```json
{"ok": false, "error": "message", "code": "ERROR_CODE"}
```

## Runtime Center

The Settings page includes a Runtime Center tab for inspecting local background
services, collector health, SQLite health, YASB status, duplicate processes, and
safe orphan cleanup previews. It uses the Python backend; the frontend never
executes system commands directly.

CLI entry points:

```powershell
daily-report runtime status
daily-report runtime status --json
daily-report runtime processes
daily-report runtime doctor
daily-report runtime cleanup-orphans --dry-run
daily-report runtime cleanup-orphans --execute
daily-report runtime repair
daily-report runtime stop-collector
daily-report runtime restart-collector
```

Safety notes:

- `daily-report status --json` remains the lightweight YASB-oriented command.
- Runtime commands only terminate processes that are clearly identified as
  manageable Daily Report roles.
- `cleanup-orphans` defaults to dry-run and does not force kill by default.
- Unknown processes with the project as cwd are observable, but automatic
  terminate/kill is rejected.
- `repair` handles stale runtime registry rows and stale collector lock files; it
  does not kill processes.

Useful troubleshooting flow:

```powershell
daily-report runtime status
daily-report runtime doctor
daily-report runtime repair
daily-report runtime cleanup-orphans --dry-run
```

## Vue API Mode

The Vue frontend uses a unified API client. Copy `frontend/.env.example` when you
need local overrides:

```env
# mock | http | qwebchannel | tauri
VITE_API_MODE=tauri
VITE_API_BASE_URL=http://127.0.0.1:8765
VITE_API_TOKEN=
```

Browser-only development can still use HTTP mode:

```powershell
daily-report api --host 127.0.0.1 --port 8765
cd frontend
npm run dev
```

Set `VITE_API_MODE=http` for normal browser development with a manually started
Python API. Set `VITE_API_MODE=mock` to work on the UI without the Python API.
Set `VITE_API_MODE=qwebchannel` when running through the existing PySide6
QWebChannel path.

## SourceAdapter Boundary

Phase 1 introduces an internal `daily_report.sources` abstraction. This does not
change the REST API contract or Vue data shapes. It moves source-specific
normalization and material conversion out of `TimelineService` and
`MaterialService`.

Enabled product sources:

- `app`: foreground application sessions from `app_sessions`
- `browser`: unified browser data from `browser_history_entries`,
  `ai_prompt_entries`, and `browser_events`
- `clipboard`: clipboard text previews from `clipboard_entries`

Browser records expose a stable product-level `source_type=browser` and an
internal `record_type`:

- `history_visit`
- `search`
- `page_view`
- `dwell_time`
- `copy`
- `ai_prompt`
- `tab_active`
- `tab_inactive`
- `page_leave`

Compatibility aliases:

- `browser_history` and `edge_history` map to `browser`
- `ai` and `ai_prompt` map to `browser` with `record_type=ai_prompt`
- `browser_event` and `browser_events` map to `browser`

Entry governance should prefer `entry_key` endpoints. `entry_annotations_v2`
stores cross-source review state such as importance, category, notes,
sensitivity, selection override, and soft deletion without depending on raw row
IDs.

Reserved adapters exist for later phases:

- `bilibili`: Phase 3 placeholder only

Browser event collection is intentionally lightweight. The Edge extension sends
records to `POST /api/events/browser` with a browser `record_type`; AI prompt
submissions are stored as browser `record_type=ai_prompt`. Search and AI prompt
records are selected by default when they are not sensitive; low-signal lifecycle
records are available for review but are not automatically treated as daily
report material.

Additional notes:

- [Browser data source design](docs/browser_data_source.md)
- [Data governance model](docs/data_governance.md)
- [Phase 2/3 unified browser implementation report](docs/phase2_phase3_unified_browser_report.md)

This phase intentionally does not add Bilibili/video collection, screenshots or
OCR, Git/mail/calendar collection, WebSocket push, cookie sync, page-body or form
input collection, vector search, or Python sidecar packaging.

## Privacy Principles

- Data is stored locally in SQLite.
- Sensitive clipboard and AI prompt records are excluded from report materials
  by default.
- Clipboard materials use `content_preview`, not full clipboard `content`.
- AI prompt materials use `prompt_preview`, not full `prompt_text`.
- App profiles can disable window-title capture; disabled titles are not exposed
  as material evidence.
- Browser history collection does not collect page body text.
- Browser behavior event collection stores lightweight metadata only. Copy event
  capture is disabled in the extension by default.
- Cookies are not synchronized.
- Model calls are made from user-selected materials.

## Tauri Development Preview

The third and fourth migration stages add a Tauri v2 desktop shell for the
existing Vue frontend. Python is still run from the development environment and
is not bundled into Tauri yet.

Install the root JavaScript dependencies once before using the Tauri scripts:

```powershell
npm install
```

Recommended script:

```powershell
npm run gui
```

This is an alias for `npm run tauri:dev:sidecar`.

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
