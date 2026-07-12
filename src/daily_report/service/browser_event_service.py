from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from daily_report.collector.ai_prompt_receiver import (
    detect_platform,
    make_dedupe_key,
    normalize_prompt,
    parse_client_timestamp,
)
from daily_report.domain.sensitivity import detect_sensitive_text, hash_text, make_preview
from daily_report.storage.database import create_connection, default_db_path, init_database
from daily_report.storage.repositories.ai_prompt_repository import AiPromptEntryRepository
from daily_report.storage.repositories.browser_event_repository import BrowserEventRepository

ACCEPTED_BROWSER_EVENT_TYPES = [
    'page_view',
    'tab_active',
    'tab_inactive',
    'page_leave',
    'dwell_time',
    'search',
    'copy',
    'ai_prompt_submit',
]

ACCEPTED_BROWSER_RECORD_TYPES = {
    'page_view',
    'search',
    'dwell_time',
    'copy',
    'ai_prompt',
    'tab_active',
    'tab_inactive',
    'page_leave',
}

DEFAULT_SELECTED_RECORD_TYPES = {'ai_prompt', 'search'}


class BrowserEventService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()

    def accept_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = self._normalize_event(payload)
        with self._connect() as conn:
            event_id, duplicated = BrowserEventRepository(conn).upsert_event(event)
        return {'id': event_id, 'duplicated': duplicated}

    def accept_ai_prompt(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry = self._ai_prompt_entry_from_payload(payload)
        with self._connect() as conn:
            entry_id, duplicated = AiPromptEntryRepository(conn).upsert_prompt(entry)
        return {
            'id': entry_id,
            'duplicated': duplicated,
            'is_sensitive': bool(entry['is_sensitive']),
            'is_selected': bool(entry['is_selected']),
        }

    def _normalize_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_type = self.normalize_event_type(payload.get('event_type') or payload.get('record_type'))
        record_type = self.normalize_record_type(payload.get('record_type'), event_type)
        timestamp = parse_client_timestamp(payload.get('timestamp'))
        url = self.normalize_url(payload.get('url'))
        title = make_preview(str(payload.get('title') or ''), 300) or None
        search_engine, search_query = self.detect_search_from_payload(payload)
        content_preview = make_preview(str(payload.get('content_preview') or payload.get('prompt_preview') or ''), 300) or None
        sensitive, reason = self.detect_sensitive_event(
            {
                'event_type': event_type,
                'record_type': record_type,
                'url': url,
                'title': title,
                'search_query': search_query,
                'content_preview': content_preview,
                'payload': payload.get('payload'),
            }
        )
        importance = self.decide_default_importance(record_type, _safe_float(payload.get('duration_sec')))
        selected = self.decide_default_selected(record_type, sensitive)
        return {
            'date': timestamp.date().isoformat(),
            'timestamp': timestamp.isoformat(timespec='seconds'),
            'record_type': record_type,
            'event_type': event_type,
            'url': url,
            'title': title,
            'domain': self.extract_domain(url),
            'tab_id': _trim(payload.get('tab_id'), 128),
            'window_id': _trim(payload.get('window_id'), 128),
            'duration_sec': _safe_float(payload.get('duration_sec')),
            'content_preview': content_preview,
            'search_engine': search_engine,
            'search_query': search_query,
            'referrer': self.normalize_url(payload.get('referrer')),
            'payload': self.build_payload_json(payload.get('payload')),
            'client_event_id': _trim(payload.get('client_event_id'), 160),
            'source': _trim(payload.get('source'), 64) or 'edge_extension',
            'importance': importance,
            'is_sensitive': sensitive,
            'sensitivity_reason': reason,
            'is_selected': selected,
        }

    @staticmethod
    def normalize_event_type(event_type: Any) -> str:
        normalized = str(event_type or '').strip()
        if normalized == 'ai_prompt':
            return 'ai_prompt_submit'
        if normalized not in ACCEPTED_BROWSER_EVENT_TYPES:
            raise ValueError(f'Unsupported browser event_type: {event_type}')
        return normalized

    @staticmethod
    def normalize_record_type(record_type: Any, event_type: str | None = None) -> str:
        normalized = str(record_type or '').strip()
        if normalized == 'ai_prompt_submit':
            normalized = 'ai_prompt'
        if not normalized:
            normalized = 'ai_prompt' if event_type == 'ai_prompt_submit' else str(event_type or '').strip()
        if normalized not in ACCEPTED_BROWSER_RECORD_TYPES:
            raise ValueError(f'Unsupported browser record_type: {record_type or event_type}')
        return normalized

    @staticmethod
    def normalize_url(url: Any) -> str | None:
        text = str(url or '').replace('\x00', '').strip()
        if not text:
            return None
        if not (text.startswith('http://') or text.startswith('https://')):
            return None
        return text[:2000]

    @staticmethod
    def extract_domain(url: str | None) -> str | None:
        try:
            host = urlparse(str(url or '')).hostname
        except Exception:
            host = None
        return host.lower()[:255] if host else None

    @staticmethod
    def detect_search_from_payload(payload: dict[str, Any]) -> tuple[str | None, str | None]:
        engine = _trim(payload.get('search_engine'), 64)
        query = make_preview(str(payload.get('search_query') or ''), 200) or None
        if engine or query:
            return engine, query
        url = str(payload.get('url') or '')
        try:
            parsed = urlparse(url)
        except Exception:
            return None, None
        host = (parsed.hostname or '').lower()
        params = dict(item.split('=', 1) for item in parsed.query.split('&') if '=' in item)
        raw_query = None
        engine = None
        if 'google.' in host and parsed.path.startswith('/search'):
            engine, raw_query = 'google', params.get('q')
        elif 'bing.com' in host and parsed.path.startswith('/search'):
            engine, raw_query = 'bing', params.get('q')
        elif 'baidu.com' in host and parsed.path.startswith('/s'):
            engine, raw_query = 'baidu', params.get('wd') or params.get('word')
        elif 'duckduckgo.com' in host:
            engine, raw_query = 'duckduckgo', params.get('q')
        elif host == 'github.com' and parsed.path.startswith('/search'):
            engine, raw_query = 'github', params.get('q')
        elif host == 'search.bilibili.com':
            engine, raw_query = 'bilibili', params.get('keyword')
        if not raw_query:
            return None, None
        from urllib.parse import unquote_plus

        return engine, make_preview(unquote_plus(raw_query), 200) or None

    @staticmethod
    def detect_sensitive_event(event: dict[str, Any]) -> tuple[bool, str | None]:
        if isinstance(event.get('payload'), dict) and bool(event['payload'].get('sensitive_hint')):
            return True, 'client:sensitive_hint'
        text = '\n'.join(
            str(value or '')
            for value in (
                event.get('url'),
                event.get('title'),
                event.get('search_query'),
                event.get('content_preview'),
            )
        )
        return detect_sensitive_text(text)

    @staticmethod
    def decide_default_importance(record_type: str, duration_sec: float = 0) -> int:
        if record_type == 'ai_prompt':
            return 90
        if record_type == 'search':
            return 70
        if record_type == 'copy':
            return 50
        if record_type == 'dwell_time':
            if duration_sec > 300:
                return 50
            if duration_sec >= 60:
                return 30
            return 10
        if record_type == 'page_view':
            return 10
        return 0

    @staticmethod
    def decide_default_selected(record_type: str, sensitive: bool) -> bool:
        if sensitive:
            return False
        return record_type in DEFAULT_SELECTED_RECORD_TYPES

    @staticmethod
    def build_payload_json(payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        safe: dict[str, Any] = {}
        for key, value in payload.items():
            clean_key = str(key or '')[:80]
            if not clean_key:
                continue
            if isinstance(value, str):
                safe[clean_key] = make_preview(value, 500)
            elif isinstance(value, (int, float, bool)) or value is None:
                safe[clean_key] = value
        return safe

    def _ai_prompt_entry_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt_text = normalize_prompt(payload.get('prompt_text'))
        if len(prompt_text) < 2:
            raise ValueError('prompt_too_short')
        conversation_url = str(payload.get('conversation_url') or '').strip()[:2048]
        page_title = str(payload.get('page_title') or '').replace('\x00', '').strip()[:512]
        timestamp = parse_client_timestamp(payload.get('timestamp') or payload.get('submitted_at'))
        platform = detect_platform(conversation_url, payload.get('platform'))
        prompt_hash = hash_text(prompt_text)
        dedupe_key = make_dedupe_key(
            platform=platform,
            conversation_url=conversation_url,
            prompt_hash=prompt_hash,
            timestamp=timestamp,
        )
        is_sensitive, reason = detect_sensitive_text(prompt_text)
        return {
            'date': timestamp.date().isoformat(),
            'timestamp': timestamp,
            'platform': platform,
            'conversation_url': conversation_url,
            'page_title': page_title,
            'prompt_text': prompt_text,
            'prompt_preview': make_preview(prompt_text, 120),
            'prompt_hash': prompt_hash,
            'dedupe_key': dedupe_key,
            'char_count': len(prompt_text),
            'is_sensitive': is_sensitive,
            'sensitivity_reason': reason,
            'is_selected': not is_sensitive,
            'client_event_id': _trim(payload.get('client_event_id'), 128),
            'source': _trim(payload.get('source'), 64) or 'edge_extension',
        }

    def _connect(self):
        conn = create_connection(self.db_path)
        init_database(conn)
        return conn


def api_time() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def _trim(value: Any, max_len: int) -> str | None:
    text = str(value or '').replace('\x00', '').strip()
    return text[:max_len] if text else None


def _safe_float(value: Any) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0
