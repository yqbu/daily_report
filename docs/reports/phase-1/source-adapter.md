# Phase 1 SourceAdapter Report

## Summary

Phase 1 introduced `daily_report.sources` as an internal source abstraction for the four current data sources. API and Vue-facing response shapes remain compatible.

## New Files

- `src/daily_report/sources/__init__.py`
- `src/daily_report/sources/base.py`
- `src/daily_report/sources/aliases.py`
- `src/daily_report/sources/registry.py`
- `src/daily_report/sources/app_source.py`
- `src/daily_report/sources/browser_source.py`
- `src/daily_report/sources/clipboard_source.py`
- `src/daily_report/sources/ai_prompt_source.py`
- `src/daily_report/sources/browser_event_source.py`
- `src/daily_report/sources/bilibili_source.py`

## Enabled Adapters

- `AppSourceAdapter`
- `BrowserSourceAdapter`
- `ClipboardSourceAdapter`
- `AIPromptSourceAdapter`

## Reserved Adapters

- `BrowserEventSourceAdapter` exists only as a Phase 2 placeholder.
- `BilibiliSourceAdapter` exists only as a Phase 3 placeholder.

They are not registered, do not create tables, and do not alter API behavior.

## TimelineService Changes

`TimelineService` now uses `SourceRegistry` as the default path:

1. Normalize requested source types through `sources.aliases`.
2. Resolve enabled adapters from `SourceRegistry`.
3. Ask each adapter for raw rows.
4. Normalize raw rows into `TimelineEvent`.
5. Keep app-session aggregation in `TimelineService`.
6. Apply category, sensitive, ordering, limit, and offset centrally.

Compatibility retained:

- `source_type=app`
- `source_type=browser`
- `source_type=browser_history`
- `source_type=edge_history`
- `source_type=clipboard`
- `source_type=ai`
- `source_type=ai_prompt`

## MaterialService Changes

`MaterialService.build_materials` now:

1. Calls `TimelineService.list_timeline(..., selected=True)`.
2. Filters deleted and sensitive events unless `include_sensitive=True`.
3. Calls the matching adapter's `to_material`.
4. Keeps the existing `source_counts` SQL path for stable performance.

Material behavior retained:

- Sensitive clipboard and AI prompts are excluded by default.
- Clipboard uses `content_preview`, not full `content`.
- AI prompts use `prompt_preview`, not full `prompt_text`.
- Browser noise records are not material unless they are searches.
- App records shorter than 10 seconds are not material.
- App profiles with `track_enabled = false` do not enter materials.
- App profiles with `capture_title_enabled = false` do not expose window titles in evidence.

## API Alias Cleanup

The following now use `sources.aliases.normalize_source_type`:

- `api/routes/timeline.py`
- `api/routes/entries.py`
- `gui/services/gui_service.py`
- `storage/repositories/annotation_repository.py`

Unsupported sources such as `browser_event` and `bilibili` still return clear errors instead of silent empty data.

## Tests

Added:

- `tests/test_source_adapters.py`

Covered:

- Default registry contains the four enabled sources.
- `browser_history` alias resolves to `browser`.
- `ai` alias resolves to `ai_prompt`.
- Invalid source types raise `ValueError`.
- TimelineService aggregates four sources through adapters.
- MaterialService uses preview-only text for clipboard and AI prompt evidence.

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Result: 21 passed.

## Deferred Work

Not implemented in Phase 1:

- Bilibili collection.
- Browser page view / dwell time / tab active events.
- `browser_events` table.
- `bilibili` table.
- Python sidecar packaging.
- `externalBin`.
- WebSocket push.
- Cookie sync.

Recommended Phase 2 start: design `browser_events` schema and browser behavior collection boundaries, then register `BrowserEventSourceAdapter` only after storage, privacy rules, and API compatibility tests are ready.
