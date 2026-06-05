from __future__ import annotations

SOURCE_TYPE_ALIASES = {
    'app': 'app',
    'browser': 'browser',
    'browser_event': 'browser_event',
    'browser_events': 'browser_event',
    'browser_history': 'browser',
    'edge_history': 'browser',
    'clipboard': 'clipboard',
    'ai': 'ai_prompt',
    'ai_prompt': 'ai_prompt',
}

ENABLED_SOURCE_TYPES = {'app', 'browser', 'clipboard', 'ai_prompt', 'browser_event'}


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
        return ['app', 'browser', 'clipboard', 'ai_prompt', 'browser_event']
    normalized: list[str] = []
    for source_type in source_types:
        item = normalize_source_type(source_type)
        if item not in normalized:
            normalized.append(item)
    return normalized
