# Phase 2/3 Unified Browser Pre-check Report

Date: 2026-06-05

## Scope

This check reviewed the Phase 2/3 target files for unifying browser history, browser extension events, and AI prompts under the product-level source:

`source_type = browser`

with browser-internal `record_type` values such as `history_visit`, `search`, `page_view`, `dwell_time`, `copy`, and `ai_prompt`.

## Findings Before Implementation

1. `SourceAdapter` existed in `src/daily_report/sources/base.py`.
2. `BrowserSourceAdapter` existed, but it only read `browser_history_entries`.
3. `AIPromptSourceAdapter` existed separately with `source_type = ai_prompt`.
4. `BrowserEventSourceAdapter` existed separately with `source_type = browser_event`.
5. `TimelineEvent` did not yet expose `record_type`, `entry_key`, `importance`, `origin_source_type`, or `origin_source_id`.
6. `MaterialCard` had `importance`, but did not yet expose `record_type` or `entry_key`.
7. `entry_annotations` was based on `source_type + source_id`.
8. No `entry_annotations_v2` table or equivalent `entry_key` annotation mechanism existed.
9. `browser_events` existed, but used `event_type` as the main type field and did not have `record_type` or `importance`.
10. The extension already posted lightweight browser events to `/api/events/browser`, but AI prompt capture still posted to `/api/ai-prompt` first and only then posted a browser event.
11. `/api/events/browser` and `/api/extension/health` already existed.
12. `DataCenter` still exposed `ai_prompt` and `browser_event` as independent source options.
13. Frontend `SourceType` still included `ai_prompt` and `browser_event`.
14. Entry annotation updates were still primarily `source_type + id` based.
15. `RecordDetailDrawer` had a governance section, but importance was limited to `0-5` and did not use `entry_key`.

## Reuse Decisions

Existing `BrowserEventRepository`, `BrowserEventService`, `/api/events/browser`, `/api/extension/health`, and the Phase 1 adapter structure were reused and extended rather than reimplemented.

Existing Vue page layouts were retained. The UI work was limited to small filters, labels, and detail fields.

