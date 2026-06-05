from __future__ import annotations

SOURCE_TYPE_ALIASES = {
    'app': 'app',
    'browser': 'browser',
    'browser_event': 'browser',
    'browser_events': 'browser',
    'browser_history': 'browser',
    'edge_history': 'browser',
    'clipboard': 'clipboard',
    'ai': 'browser',
    'ai_prompt': 'browser',
}

LEGACY_RECORD_TYPE_BY_SOURCE = {
    'ai': 'ai_prompt',
    'ai_prompt': 'ai_prompt',
}

ENABLED_SOURCE_TYPES = {'app', 'browser', 'clipboard'}


def normalize_source_type(source_type: str) -> str:
    normalized = str(source_type or '').strip()
    if not normalized:
        raise ValueError('Unsupported source_type: empty')
    try:
        return SOURCE_TYPE_ALIASES[normalized]
    except KeyError as exc:
        raise ValueError(f'Unsupported source_type: {source_type}') from exc


def normalize_source_types(source_types: list[str] | None) -> list[str]:
    if not source_types:
        return ['app', 'browser', 'clipboard']
    normalized: list[str] = []
    for source_type in source_types:
        item = normalize_source_type(source_type)
        if item not in normalized:
            normalized.append(item)
    return normalized
