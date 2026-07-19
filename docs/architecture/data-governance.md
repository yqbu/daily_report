# Data Governance

Phase 2/3 adds `entry_annotations_v2`, an entry-key based governance table.

The old `entry_annotations` table remains available for compatibility and is not rebuilt.

## New Table

`entry_annotations_v2` stores:

- `entry_key`
- `source_type`
- `record_type`
- `category`
- `note`
- `importance`
- `is_selected_override`
- `is_sensitive_override`
- `sensitivity_reason_override`

## API

New by-key APIs:

- `GET /api/entries/by-key/{entry_key}`
- `PATCH /api/entries/by-key/selection`
- `PATCH /api/entries/by-key/deleted`
- `PATCH /api/entries/by-key/annotation`
- `PATCH /api/entries/by-key/sensitive`

The frontend prefers by-key updates when `entry_key` is available. Legacy `source_type + id` APIs remain for older code paths.

## Selection And Sensitivity

Manual selection and sensitivity changes are persisted as overrides. Sensitive records are excluded from report materials unless explicitly handled by the user.

Importance is clamped to `0-100`.

