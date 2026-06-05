# Daily Report Architecture

## Current Phase

The project is in migration Phase 5:

- Tauri v2 is the primary desktop shell.
- Vue 3 is the primary UI.
- Python FastAPI is the local sidecar API boundary.
- SQLite is the local storage layer.
- Python collector, service, reporter, and storage modules remain the business core.
- PySide6 is kept only as a legacy fallback.
- Python is not bundled yet. Phase 6 is reserved for sidecar packaging.

## Runtime Chain

Recommended managed development chain:

```text
daily-report gui
  -> npm run tauri:dev:sidecar
  -> Tauri starts local Python API on 127.0.0.1
  -> Tauri generates bearer token and runtime config
  -> Vue reads get_runtime_config
  -> Vue calls FastAPI over HTTP
```

Manual development chain:

```text
daily-report api --host 127.0.0.1 --port 8765
  -> npm run tauri:dev
  -> Vue uses runtime fallback / VITE_API_BASE_URL
```

## Local API

Health endpoints are public:

- `GET /api/health`
- `GET /api/health/collectors`
- `GET /api/extension/health`

Business endpoints are protected when an API token is configured:

- `GET /api/overview`
- `GET /api/timeline`
- `GET /api/entries/{source_type}`
- `GET /api/entries/{source_type}/{id}`
- `PATCH /api/entries/{source_type}/{id}/selection`
- `PATCH /api/entries/{source_type}/{id}/deleted`
- `POST /api/events/browser`
- `POST /api/ai-prompt`
- `POST /api/reports/build-prompt`
- `POST /api/reports/generate`
- `GET /api/reports/latest`
- `GET /api/settings`
- `PUT /api/settings`

Responses use:

```json
{"ok": true, "data": {}}
```

```json
{"ok": false, "error": "message", "code": "ERROR_CODE"}
```

## SourceAdapter

Phase 1 adds `daily_report.sources` as an internal source abstraction. The public API remains stable.

Enabled adapters:

- `AppSourceAdapter` for `app_sessions`
- `BrowserSourceAdapter` for `browser_history_entries`
- `ClipboardSourceAdapter` for `clipboard_entries`
- `AIPromptSourceAdapter` for `ai_prompt_entries`
- `BrowserEventSourceAdapter` for `browser_events`

Reserved placeholders:

- `BilibiliSourceAdapter` for Phase 3 Bilibili viewing data

Current aliases:

- `browser_history` and `edge_history` normalize to `browser`
- `ai` normalizes to `ai_prompt`
- `browser_events` normalizes to `browser_event`

## Browser Events

The Edge/Chromium extension posts lightweight behavior events to
`POST /api/events/browser`. Supported event types are:

- `page_view`
- `tab_active`
- `tab_inactive`
- `page_leave`
- `dwell_time`
- `search`
- `copy`
- `ai_prompt_submit`

The extension does not collect page body text, form input, cookies, screenshots,
or OCR. Copy event support exists but is disabled by default. Sensitive events
are stored with `is_sensitive = 1` and are not selected for report material.

## Privacy Principles

- Data stays in local SQLite.
- Sensitive clipboard and AI prompt records are excluded from report materials by default.
- Clipboard and AI prompt materials use preview text, not full raw text.
- App profile `capture_title_enabled = false` prevents window-title evidence from entering materials.
- Browser collection uses history metadata. It does not collect page body text.
- Browser behavior events use metadata only; search events are the only browser
  event type selected by default.
- Cookies are not synchronized.
- Model calls use user-selected materials.
