# Unified Browser Data Source

Phase 2/3 treats browser history, browser extension events, and AI prompt submissions as one product-level source:

`source_type = browser`

Browser records are differentiated by `record_type`:

- `history_visit`: imported browser history visit
- `search`: search behavior from history or extension events
- `page_view`: extension page view event
- `dwell_time`: extension dwell-time event
- `copy`: extension copy preview event
- `ai_prompt`: ChatGPT / DeepSeek prompt submission
- `tab_active`, `tab_inactive`, `page_leave`: lightweight tab lifecycle events

The short-term storage layer still keeps multiple raw tables:

- `browser_history_entries`
- `ai_prompt_entries` as legacy history
- `browser_events`

The service layer normalizes all of them through `BrowserSourceAdapter` and returns timeline/material records as `source_type=browser`.

## Entry Keys

Each normalized record has a stable `entry_key`:

- `browser:history:{id}`
- `browser:ai_prompt:{id}`
- `browser:event:{id}`

This lets the product layer govern records safely even when one logical source reads multiple raw tables.

## Importance Defaults

- `ai_prompt`: 90
- `search`: 70
- `copy`: 50
- `dwell_time`: 10, 30, or 50 depending on duration
- `history_visit`: 30, or 10 for noisy visits
- `page_view`: 10
- `tab_active`, `tab_inactive`, `page_leave`: 0

Sensitive records are not selected by default.

## Privacy Principles

The browser extension does not collect page body text, ordinary form input, password fields, cookies, localStorage, or sessionStorage.

AI prompt capture is limited to ChatGPT / DeepSeek prompt boxes and is submitted as `record_type=ai_prompt`. The new primary endpoint is `/api/events/browser`; `/api/ai-prompt` remains a legacy fallback endpoint.

Bilibili-specific video collection is intentionally left for a later phase.

