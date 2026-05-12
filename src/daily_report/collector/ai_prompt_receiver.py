from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional, Protocol
from urllib.parse import urlparse

from daily_report.storage.database import (
    SqliteConnectionFactory,
    create_connection,
    default_db_path,
    init_database,
)
from daily_report.storage.storage_adapter.ai_prompt_store import (
    RepositoryAiPromptEntryStore,
)

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_ENDPOINT = "/api/ai-prompts"
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_PROMPT_CHARS = 20_000

SENSITIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S+"), "password-like content"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|access[_-]?token|refresh[_-]?token)\s*[:=]\s*\S+"), "token/key-like content"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI-like API key"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}"), "Bearer token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "JWT-like token"),
]


@dataclass
class AiPromptEntryState:
    id: Optional[int]
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
    sensitivity_reason: Optional[str]
    is_selected: bool
    client_event_id: Optional[str]
    source: str


class AiPromptEntryStore(Protocol):
    def save_entry(self, entry: AiPromptEntryState) -> int:
        ...

    def close(self) -> None:
        ...


def normalize_prompt(text: Any) -> str:
    if text is None:
        return ""

    value = str(text).replace("\x00", "")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()[:MAX_PROMPT_CHARS]


def make_preview(text: str, max_chars: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1] + "…"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def parse_client_timestamp(value: Any) -> datetime:
    if not value:
        return datetime.now()

    if isinstance(value, (int, float)):
        # JS Date.now() milliseconds are much larger than normal Unix seconds.
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000.0
        return datetime.fromtimestamp(timestamp)

    text = str(value).strip()
    if not text:
        return datetime.now()

    try:
        # Accept ISO strings produced by new Date().toISOString().
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return datetime.now()


def detect_platform(conversation_url: str, declared_platform: Any = None) -> str:
    declared = str(declared_platform or "").strip()
    if declared:
        normalized = declared.lower()
        if "deepseek" in normalized:
            return "DeepSeek"
        if "chatgpt" in normalized or "openai" in normalized:
            return "ChatGPT"
        return declared[:64]

    try:
        host = (urlparse(conversation_url).hostname or "").lower()
    except Exception:
        host = ""

    if "deepseek" in host:
        return "DeepSeek"
    if "chatgpt" in host or "openai" in host:
        return "ChatGPT"
    return "Unknown"


def detect_sensitive(prompt_text: str) -> tuple[bool, Optional[str]]:
    for pattern, reason in SENSITIVE_PATTERNS:
        if pattern.search(prompt_text):
            return True, reason
    return False, None


def make_dedupe_key(
    *,
    platform: str,
    conversation_url: str,
    prompt_hash: str,
    timestamp: datetime,
    bucket_seconds: int = 10,
) -> str:
    """
    以 10 秒为桶做去重，避免 keydown/click/submit 多路事件重复入库。

    同一平台、同一会话 URL、同一 prompt，在 10 秒内只保留一条。
    """
    epoch = int(timestamp.replace(tzinfo=timezone.utc).timestamp())
    bucket = epoch // bucket_seconds
    raw = f"{platform}|{conversation_url}|{prompt_hash}|{bucket}"
    return sha256_text(raw)


class AiPromptReceiver:
    """
    ChatGPT / DeepSeek Prompt 本地接收器。

    Edge extension content_script 会将用户发送的问题 POST 到：
        http://127.0.0.1:8765/api/ai-prompts

    该 receiver 负责：
    - 接收 JSON payload；
    - 做基础校验、规范化、敏感内容标记；
    - 写入 ai_prompt_entries 表。

    与现有 CollectorManager 兼容，提供 start(blocking=False)、stop()。
    """

    name: str = "ai_prompt_receiver"

    def __init__(
        self,
        store: AiPromptEntryStore,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        endpoint: str = DEFAULT_ENDPOINT,
        auth_token: Optional[str] = None,
        min_prompt_chars: int = 2,
    ):
        self.store = store
        self.host = host
        self.port = int(port)
        self.endpoint = endpoint
        self.auth_token = auth_token if auth_token is not None else os.getenv("DAILY_REPORT_AI_PROMPT_TOKEN", "").strip() or None
        self.min_prompt_chars = int(min_prompt_chars)

        self._stop_event = threading.Event()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = False) -> Optional[threading.Thread]:
        if blocking:
            self.run_forever()
            return None

        thread = threading.Thread(
            target=self.run_forever,
            name="AiPromptReceiver",
            daemon=True,
        )
        self._thread = thread
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                logger.exception("Failed to shutdown AiPromptReceiver HTTP server.")

    def run_forever(self) -> None:
        handler_cls = self._make_handler_class()
        self._server = HTTPServer((self.host, self.port), handler_cls)

        if self.auth_token:
            logger.info("AiPromptReceiver token auth enabled.")
        else:
            logger.warning(
                "AiPromptReceiver token auth is disabled. "
                "For local MVP this is acceptable, but setting DAILY_REPORT_AI_PROMPT_TOKEN is safer."
            )

        logger.info("AiPromptReceiver started at http://%s:%s%s", self.host, self.port, self.endpoint)

        try:
            self._server.serve_forever(poll_interval=0.5)
        finally:
            try:
                self._server.server_close()
            finally:
                self._close_store()
                logger.info("AiPromptReceiver stopped.")

    def _make_handler_class(self) -> type[BaseHTTPRequestHandler]:
        receiver = self

        class RequestHandler(BaseHTTPRequestHandler):
            server_version = "DailyReportAiPromptReceiver/0.1"

            def do_OPTIONS(self) -> None:  # noqa: N802
                self._send_cors_response(204, {})

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health" or self.path == f"{receiver.endpoint}/health":
                    self._send_json(200, {"ok": True, "name": receiver.name})
                    return
                self._send_json(404, {"ok": False, "error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                if self.path != receiver.endpoint:
                    self._send_json(404, {"ok": False, "error": "not_found"})
                    return

                if receiver.auth_token:
                    request_token = self.headers.get("X-Daily-Report-Token", "")
                    if request_token != receiver.auth_token:
                        self._send_json(401, {"ok": False, "error": "unauthorized"})
                        return

                try:
                    payload = self._read_json_body()
                    entry = receiver._entry_from_payload(payload)
                    entry.id = receiver.store.save_entry(entry)
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "id": entry.id,
                            "is_sensitive": entry.is_sensitive,
                            "is_selected": entry.is_selected,
                        },
                    )
                except ValueError as exc:
                    self._send_json(400, {"ok": False, "error": str(exc)})
                except Exception:
                    logger.exception("Failed to save AI prompt entry.")
                    self._send_json(500, {"ok": False, "error": "internal_error"})

            def log_message(self, fmt: str, *args: Any) -> None:
                logger.debug("AiPromptReceiver HTTP: " + fmt, *args)

            def _read_json_body(self) -> dict[str, Any]:
                content_length = int(self.headers.get("Content-Length", "0") or 0)
                if content_length <= 0:
                    raise ValueError("empty_body")
                if content_length > MAX_BODY_BYTES:
                    raise ValueError("body_too_large")

                raw = self.rfile.read(content_length)
                try:
                    data = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise ValueError("invalid_json") from exc

                if not isinstance(data, dict):
                    raise ValueError("json_body_must_be_object")
                return data

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                self._send_cors_response(status, payload)

            def _send_cors_response(self, status: int, payload: dict[str, Any]) -> None:
                body = b"" if status == 204 else json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Daily-Report-Token")
                self.send_header("Access-Control-Max-Age", "86400")
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

        return RequestHandler

    def _entry_from_payload(self, payload: dict[str, Any]) -> AiPromptEntryState:
        prompt_text = normalize_prompt(payload.get("prompt_text"))
        if len(prompt_text) < self.min_prompt_chars:
            raise ValueError("prompt_too_short")

        conversation_url = str(payload.get("conversation_url") or "").strip()[:2048]
        page_title = str(payload.get("page_title") or "").replace("\x00", "").strip()[:512]
        platform = detect_platform(conversation_url, payload.get("platform"))

        timestamp = parse_client_timestamp(payload.get("submitted_at") or payload.get("timestamp"))
        prompt_hash = sha256_text(prompt_text)
        dedupe_key = make_dedupe_key(
            platform=platform,
            conversation_url=conversation_url,
            prompt_hash=prompt_hash,
            timestamp=timestamp,
        )

        is_sensitive, sensitivity_reason = detect_sensitive(prompt_text)

        return AiPromptEntryState(
            id=None,
            date=timestamp.date().isoformat(),
            timestamp=timestamp,
            platform=platform,
            conversation_url=conversation_url,
            page_title=page_title,
            prompt_text=prompt_text,
            prompt_preview=make_preview(prompt_text),
            prompt_hash=prompt_hash,
            dedupe_key=dedupe_key,
            char_count=len(prompt_text),
            is_sensitive=is_sensitive,
            sensitivity_reason=sensitivity_reason,
            is_selected=not is_sensitive,
            client_event_id=str(payload.get("client_event_id") or "").strip()[:128] or None,
            source=str(payload.get("source") or "edge_extension").strip()[:64],
        )

    def _close_store(self) -> None:
        close = getattr(self.store, "close", None)
        if callable(close):
            close()


def debug_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )

    db_path = default_db_path()
    logger.info("SQLite database path: %s", db_path)

    conn = create_connection(db_path)
    try:
        init_database(conn)
    finally:
        conn.close()

    connection_factory = SqliteConnectionFactory(db_path)
    store = RepositoryAiPromptEntryStore(connection_factory)
    receiver = AiPromptReceiver(store=store)

    try:
        receiver.run_forever()
    except KeyboardInterrupt:
        receiver.stop()
        time.sleep(0.2)


if __name__ == "__main__":
    debug_main()
