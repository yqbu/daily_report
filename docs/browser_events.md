# Browser Events

## Goal

`browser_events` adds lightweight browser behavior context to Daily Report. It is
designed to help recover useful research trails without collecting webpage body
content or private browser state.

## Collected Events

The extension can send these event types:

- `page_view`
- `tab_active`
- `tab_inactive`
- `page_leave`
- `dwell_time`
- `search`
- `copy`
- `ai_prompt_submit`

Only `search` is selected by default when the event is not sensitive. `copy` and
long `dwell_time` events can become material only after they are selected.

## Storage

Events are stored in the SQLite `browser_events` table. Important columns:

- `date`, `timestamp`, `event_type`
- `url`, `title`, `domain`, `referrer`
- `duration_sec`
- `search_engine`, `search_query`
- `content_preview`
- `payload_json`
- `client_event_id`
- `is_sensitive`, `sensitivity_reason`, `is_selected`, `is_deleted`

`client_event_id` is used for idempotent ingestion.

## API

Public health endpoint:

```http
GET /api/extension/health
```

Protected ingest endpoint:

```http
POST /api/events/browser
```

When an API token is configured, the extension may send either:

```http
Authorization: Bearer <token>
```

or:

```http
X-Daily-Report-Token: <token>
```

Legacy AI prompt compatibility is available at:

```http
POST /api/ai-prompt
POST /api/ai-prompts
```

## Privacy Boundary

The extension must not collect:

- webpage body text
- arbitrary form input
- passwords or credential fields
- cookies
- screenshots or OCR
- browsing recommendations or chat messages
- mail, calendar, Git, or video-platform watch data

The content script skips local/private hosts and several sensitive account,
payment, login, and mail-like domains. Copy collection is present but disabled
by default through `CONFIG.collectCopy = false`.
