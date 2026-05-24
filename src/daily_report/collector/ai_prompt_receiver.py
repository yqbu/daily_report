from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Protocol
from urllib.parse import urlparse

from daily_report.service.sensitivity import detect_sensitive_text, hash_text, make_preview
from daily_report.storage.database import (
    SqliteConnectionFactory,
    create_connection,
    default_db_path,
    init_database,
)
from daily_report.storage.storage_adapter.ai_prompt_store import RepositoryAiPromptEntryStore

logger = logging.getLogger(__name__)

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8765
DEFAULT_ENDPOINT = '/api/ai-prompt'
LEGACY_ENDPOINT = '/api/ai-prompts'
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_PROMPT_CHARS = 20_000


@dataclass
class AiPromptEntryState:
    id: int | None
    date: str
    timestamp: datetime
    platform: str
    conversation_url: str
    page_title: str
    prompt_text: str
    prompt_preview: str
    prompt_hash: str
    dedupe_key: str
    char_count: int
    is_sensitive: bool
    sensitivity_reason: str | None
    is_selected: bool
    client_event_id: str | None
    source: str


class AiPromptEntryStore(Protocol):
    def save_entry(self, entry: AiPromptEntryState) -> int | tuple[int, bool]:
        ...

    def close(self) -> None:
        ...


def normalize_prompt(text: Any) -> str:
    value = str(text or '').replace('\x00', '')
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    value = '\n'.join(line.rstrip() for line in value.split('\n'))
    while '\n\n\n' in value:
        value = value.replace('\n\n\n', '\n\n')
    return value.strip()[:MAX_PROMPT_CHARS]


def parse_client_timestamp(value: Any) -> datetime:
    if not value:
        return datetime.now()
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        return datetime.fromtimestamp(timestamp)

    text = str(value).strip()
    if not text:
        return datetime.now()
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return datetime.now()
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def detect_platform(conversation_url: str, declared_platform: Any = None) -> str:
    declared = str(declared_platform or '').strip()
    if declared:
        normalized = declared.lower()
        if 'deepseek' in normalized:
            return 'DeepSeek'
        if 'chatgpt' in normalized or 'openai' in normalized:
            return 'ChatGPT'
        return declared[:64]

    try:
        host = (urlparse(conversation_url).hostname or '').lower()
    except Exception:
        host = ''

    if 'deepseek' in host:
        return 'DeepSeek'
    if 'chatgpt' in host or 'openai' in host:
        return 'ChatGPT'
    return 'Unknown'


def make_dedupe_key(
    *,
    platform: str,
    conversation_url: str,
    prompt_hash: str,
    timestamp: datetime,
    bucket_seconds: int = 10,
) -> str:
    epoch = int(timestamp.replace(tzinfo=timezone.utc).timestamp())
    bucket = epoch // bucket_seconds
    return hash_text(f'{platform}|{conversation_url}|{prompt_hash}|{bucket}')


class AiPromptReceiver:
    """Local HTTP receiver for ChatGPT / DeepSeek user-submitted prompts."""

    name: str = 'ai_prompt_receiver'

    def __init__(
        self,
        store: AiPromptEntryStore,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        endpoint: str = DEFAULT_ENDPOINT,
        auth_token: str | None = None,
        min_prompt_chars: int = 2,
        sensitive_unselected_by_default: bool = True,
        sensitive_keywords: list[str] | None = None,
    ):
        self.store = store
        self.host = host
        self.port = int(port)
        self.endpoint = endpoint
        self.accepted_endpoints = {endpoint, DEFAULT_ENDPOINT, LEGACY_ENDPOINT}
        self.auth_token = auth_token if auth_token is not None else (
            os.getenv('DAILY_REPORT_AI_PROMPT_TOKEN', '').strip() or None
        )
        self.min_prompt_chars = int(min_prompt_chars)
        self.sensitive_unselected_by_default = sensitive_unselected_by_default
        self.sensitive_keywords = [kw.strip() for kw in (sensitive_keywords or []) if kw.strip()]

        self._stop_event = threading.Event()
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self, blocking: bool = False) -> threading.Thread | None:
        self._ensure_server()
        if blocking:
            self.run_forever()
            return None

        thread = threading.Thread(target=self.run_forever, name='AiPromptReceiver', daemon=True)
        self._thread = thread
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                logger.exception('Failed to shutdown AiPromptReceiver HTTP server.')

    def run_forever(self) -> None:
        self._ensure_server()
        if self.auth_token:
            logger.info('AiPromptReceiver token auth enabled.')
        logger.info('AiPromptReceiver started at http://%s:%s%s', self.host, self.port, self.endpoint)

        try:
            self._server.serve_forever(poll_interval=0.5)
        except Exception:
            logger.exception('AiPromptReceiver failed.')
            raise
        finally:
            try:
                if self._server is not None:
                    self._server.server_close()
            finally:
                self._close_store()
                logger.info('AiPromptReceiver stopped.')

    def _ensure_server(self) -> None:
        if self._server is not None:
            return
        self._server = HTTPServer((self.host, self.port), self._make_handler_class())

    def _make_handler_class(self) -> type[BaseHTTPRequestHandler]:
        receiver = self

        class RequestHandler(BaseHTTPRequestHandler):
            server_version = 'DailyReportAiPromptReceiver/0.1'

            def do_OPTIONS(self) -> None:  # noqa: N802
                self._send_json(204, {})

            def do_GET(self) -> None:  # noqa: N802
                if self.path in {'/health', f'{receiver.endpoint}/health'}:
                    self._send_json(200, {'ok': True, 'name': receiver.name})
                    return
                self._send_json(404, {'ok': False, 'error': 'not_found'})

            def do_POST(self) -> None:  # noqa: N802
                if self.path not in receiver.accepted_endpoints:
                    self._send_json(404, {'ok': False, 'error': 'not_found'})
                    return
                if receiver.auth_token:
                    request_token = self.headers.get('X-Daily-Report-Token', '')
                    if request_token != receiver.auth_token:
                        self._send_json(401, {'ok': False, 'error': 'unauthorized'})
                        return

                try:
                    payload = self._read_json_body()
                    entry = receiver._entry_from_payload(payload)
                    saved = receiver.store.save_entry(entry)
                    if isinstance(saved, tuple):
                        entry.id, duplicated = int(saved[0]), bool(saved[1])
                    else:
                        entry.id, duplicated = int(saved), False
                    self._send_json(
                        200,
                        {
                            'ok': True,
                            'id': entry.id,
                            'duplicated': duplicated,
                            'is_sensitive': entry.is_sensitive,
                            'is_selected': entry.is_selected,
                        },
                    )
                except ValueError as exc:
                    self._send_json(400, {'ok': False, 'error': str(exc)})
                except Exception:
                    logger.exception('Failed to save AI prompt entry.')
                    self._send_json(500, {'ok': False, 'error': 'internal_error'})

            def log_message(self, fmt: str, *args: Any) -> None:
                logger.debug('AiPromptReceiver HTTP: ' + fmt, *args)

            def _read_json_body(self) -> dict[str, Any]:
                try:
                    content_length = int(self.headers.get('Content-Length', '0') or 0)
                except ValueError as exc:
                    raise ValueError('invalid_content_length') from exc
                if content_length <= 0:
                    raise ValueError('empty_body')
                if content_length > MAX_BODY_BYTES:
                    raise ValueError('body_too_large')
                raw = self.rfile.read(content_length)
                try:
                    data = json.loads(raw.decode('utf-8'))
                except json.JSONDecodeError as exc:
                    raise ValueError('invalid_json') from exc
                if not isinstance(data, dict):
                    raise ValueError('json_body_must_be_object')
                return data

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                body = b'' if status == 204 else json.dumps(payload, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Daily-Report-Token')
                self.send_header('Access-Control-Max-Age', '86400')
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

        return RequestHandler

    def _entry_from_payload(self, payload: dict[str, Any]) -> AiPromptEntryState:
        prompt_text = normalize_prompt(payload.get('prompt_text'))
        if len(prompt_text) < self.min_prompt_chars:
            raise ValueError('prompt_too_short')

        conversation_url = str(payload.get('conversation_url') or '').strip()[:2048]
        page_title = str(payload.get('page_title') or '').replace('\x00', '').strip()[:512]
        platform = detect_platform(conversation_url, payload.get('platform'))
        timestamp = parse_client_timestamp(payload.get('timestamp') or payload.get('submitted_at'))
        prompt_hash = hash_text(prompt_text)
        dedupe_key = make_dedupe_key(
            platform=platform,
            conversation_url=conversation_url,
            prompt_hash=prompt_hash,
            timestamp=timestamp,
        )

        is_sensitive, sensitivity_reason = detect_sensitive_text(prompt_text)
        if not is_sensitive:
            is_sensitive, sensitivity_reason = self._detect_sensitive_keyword(prompt_text)

        return AiPromptEntryState(
            id=None,
            date=timestamp.date().isoformat(),
            timestamp=timestamp,
            platform=platform,
            conversation_url=conversation_url,
            page_title=page_title,
            prompt_text=prompt_text,
            prompt_preview=make_preview(prompt_text, 120),
            prompt_hash=prompt_hash,
            dedupe_key=dedupe_key,
            char_count=len(prompt_text),
            is_sensitive=is_sensitive,
            sensitivity_reason=sensitivity_reason,
            is_selected=(not is_sensitive) if self.sensitive_unselected_by_default else True,
            client_event_id=str(payload.get('client_event_id') or '').strip()[:128] or None,
            source=str(payload.get('source') or 'edge_extension').strip()[:64],
        )

    def _detect_sensitive_keyword(self, text: str) -> tuple[bool, str | None]:
        lower_text = text.lower()
        for keyword in self.sensitive_keywords:
            if keyword.lower() in lower_text:
                return True, f'keyword:{keyword}'
        return False, None

    def _close_store(self) -> None:
        close = getattr(self.store, 'close', None)
        if callable(close):
            close()


def debug_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    )
    db_path = default_db_path()
    logger.info('SQLite database path: %s', db_path)

    conn = create_connection(db_path)
    try:
        init_database(conn)
    finally:
        conn.close()

    store = RepositoryAiPromptEntryStore(SqliteConnectionFactory(db_path))
    receiver = AiPromptReceiver(store=store)
    try:
        receiver.run_forever()
    except KeyboardInterrupt:
        receiver.stop()
        time.sleep(0.2)


if __name__ == '__main__':
    debug_main()
