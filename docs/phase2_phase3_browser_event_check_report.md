# Phase 2/3 Browser Event Implementation Report

Date: 2026-06-04

## Scope Implemented

- Added `browser_events` SQLite table, safe migrations, and indexes.
- Added `BrowserEventRepository` and `BrowserEventService`.
- Added FastAPI endpoints:
  - `GET /api/extension/health`
  - `POST /api/events/browser`
  - `POST /api/ai-prompt`
  - `POST /api/ai-prompts`
- Registered `browser_event` in the SourceAdapter registry.
- Connected browser events to Timeline, Entries, MaterialService, Overview, GUI
  summaries, YASB status payloads, cleanup retention, and report source counts.
- Expanded the Edge/Chromium extension from AI prompt capture to lightweight
  behavior event capture.
- Added minimal Vue/Tauri UI support in Data Center, Today Overview, and Report
  Workbench source labels/filters.

## Privacy Decisions

- Search events are selected by default only when non-sensitive.
- Sensitive events are automatically unselected.
- Copy collection is implemented but disabled by default in the extension.
- Browser events do not use the legacy `entry_annotations` table because that
  table has an existing source-type CHECK constraint. `browser_events` stores
  selection, deletion, and sensitivity fields directly.

## Explicitly Not Implemented

- Bilibili/video collection
- screenshots or OCR
- Git, mail, calendar, or recommendation/chat integrations
- WebSocket push
- cookie sync
- webpage body or arbitrary form input collection
- Python sidecar packaging
- large UI redesign

## Verification

- `python -m compileall src/daily_report`
- `npm run frontend:build`
- `.\.venv\Scripts\python.exe -m pytest tests -q --basetemp .pytest_tmp_run/base -o cache_dir=.pytest_tmp_run/cache`

Result:

- Python compile: passed.
- Frontend build: passed.
- Tests: 24 passed.

Notes:

- Running tests with default Python failed because that interpreter did not have
  `pytest`.
- Running tests with the project `.venv` and default temp directory failed due to
  a Windows permission issue under `C:\Users\24331\AppData\Local\Temp`.
  Re-running with a project-local basetemp passed.
