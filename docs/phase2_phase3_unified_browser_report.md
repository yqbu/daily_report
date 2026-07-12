# Phase 2/3 Unified Browser Implementation Report

Date: 2026-06-05

## Summary

Browser history, browser extension events, and AI prompts now normalize to one product-level source:

`source_type = browser`

The internal browser type is exposed as `record_type`.

## Database

Added or extended:

- `browser_events.record_type`
- `browser_events.importance`
- `entry_annotations_v2`
- indexes for browser event `record_type`, event de-dupe, and entry-key annotation lookup

Migrations are idempotent and preserve existing raw tables.

## Backend

`BrowserSourceAdapter` now reads:

- `browser_history_entries`
- `ai_prompt_entries`
- `browser_events`

It emits:

- `entry_key`
- `record_type`
- `importance`
- `origin_source_type`
- `origin_source_id`

Legacy `source_type=ai_prompt`, `source_type=ai`, and `source_type=browser_event` aliases are mapped into `browser`.

## APIs

Added:

- `GET /api/timeline?source_type=browser&record_type=...`
- `GET /api/entries/browser?record_type=...`
- `GET /api/entries/by-key/{entry_key}`
- `PATCH /api/entries/by-key/selection`
- `PATCH /api/entries/by-key/deleted`
- `PATCH /api/entries/by-key/annotation`
- `PATCH /api/entries/by-key/sensitive`

Kept:

- `/api/events/browser`
- `/api/extension/health`
- legacy `/api/ai-prompt`

## Frontend

Data Center now shows browser as a unified primary source and adds browser record-type chips.

Record details show `record_type`, `entry_key`, importance, and origin source fields. Importance is editable from `0-100`.

Today Overview keeps the same layout and folds browser internals into the existing browser metric helper text.

Report Workbench shows browser materials as unified browser materials, with internal record type labels.

## Verification

Passed:

- `.venv\Scripts\python.exe -m pytest`
- `npm run build` in `frontend`

Known warnings:

- Existing FastAPI/TestClient and Pydantic deprecation warnings.
- Existing Vite chunk-size warnings.

## Deferred

Not implemented in this phase:

- Bilibili video collection
- screenshots / OCR / visual model
- WebSocket push
- cookie sync
- recommendation or chat systems
- full UI redesign

Bilibili collection should start later from a separate source/collector design, not from this unified browser source change.

