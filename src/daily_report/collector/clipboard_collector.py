from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol

import win32clipboard
import win32con

logger = logging.getLogger(__name__)


@dataclass
class ClipboardEntryState:
    id: Optional[int]
    date: str
    first_seen_at: datetime
    last_seen_at: datetime
    content: str
    content_preview: str
    content_hash: str
    char_count: int
    is_sensitive: bool
    sensitivity_reason: Optional[str]
    is_selected: bool


class ClipboardEntryStore(Protocol):
    def save_entry(self, entry: ClipboardEntryState) -> int:
        ...

    def close(self) -> None:
        ...


SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        'private_key',
        re.compile(
            r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            re.IGNORECASE,
        ),
    ),
    (
        'password_like',
        re.compile(
            '\\b(password|passwd|pwd)\\s*[:=]\\s*[\'\\"]?[^\'\\"\\s]{6,}',
            re.IGNORECASE,
        ),
    ),
    (
        'token_like',
        re.compile(
            '\\b(token|secret|api[_-]?key|access[_-]?key)\\s*[:=]\\s*[\'\\"]?[^\'\\"\\s]{8,}',
            re.IGNORECASE,
        ),
    ),
    (
        'bearer_token',
        re.compile(
            r'\bBearer\s+[A-Za-z0-9._~+/=-]{20,}',
            re.IGNORECASE,
        ),
    ),
    (
        'jwt',
        re.compile(
            r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'
        ),
    ),
    (
        'sk_key',
        re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    ),
    (
        'aws_access_key',
        re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    ),
]


def read_clipboard_text() -> Optional[str]:
    """
    读取 Windows 剪贴板文本

    只处理 CF_UNICODETEXT:
    - 文本: 返回 str
    - 图片、文件、二进制对象: 返回 None
    - 剪贴板被其他程序占用: 返回 None
    """
    try:
        win32clipboard.OpenClipboard()
        try:
            if not win32clipboard.IsClipboardFormatAvailable(
                win32con.CF_UNICODETEXT
            ):
                return None

            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)

        finally:
            win32clipboard.CloseClipboard()

    except Exception:
        logger.debug('Failed to read clipboard.', exc_info=True)
        return None

    if not isinstance(data, str):
        return None

    text = data.replace('\x00', '')
    text = normalize_clipboard_text(text)

    if not text:
        return None

    return text


def normalize_clipboard_text(text: str) -> str:
    """
    用于去重和存储的轻量规范化

    不做过强清洗, 避免破坏代码/命令/路径等内容
    """
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()


def make_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def make_preview(text: str, max_chars: int = 160) -> str:
    preview = re.sub(r'\s+', ' ', text).strip()
    if len(preview) <= max_chars:
        return preview
    return preview[:max_chars] + '...'


def detect_sensitive(text: str) -> tuple[bool, Optional[str]]:
    for reason, pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return True, reason

    stripped = text.strip()

    # 单独复制的一长串 token / hash / key,也默认认为可疑
    if 32 <= len(stripped) <= 300:
        if re.fullmatch(r'[A-Za-z0-9_./+=:-]{32,}', stripped):
            return True, 'possible_secret_token'

    return False, None


class ClipboardCollector:
    """
    剪贴板采集器

    特点:
    - 只记录文本
    - 轮询读取
    - 当前进程内用 _last_hash 避免每秒重复写
    - 数据库层再用 UNIQUE(date, content_hash) 做二次去重
    - 敏感内容默认 is_selected=False
    """

    name: str = 'clipboard'

    def __init__(
        self,
        store: ClipboardEntryStore,
        poll_interval_sec: float = 1.0,
        min_text_chars: int = 2,
        max_text_chars: int = 10_000,
        preview_chars: int = 160,
        sensitive_unselected_by_default: bool = True,
        sensitive_keywords: list[str] | None = None,
        clipboard_preview_only: bool = False,
    ):
        self.store = store
        self.poll_interval_sec = poll_interval_sec
        self.min_text_chars = min_text_chars
        self.max_text_chars = max_text_chars
        self.preview_chars = preview_chars
        self.sensitive_unselected_by_default = sensitive_unselected_by_default
        self.sensitive_keywords = [kw.strip() for kw in (sensitive_keywords or []) if kw.strip()]
        self.clipboard_preview_only = clipboard_preview_only

        self._stop_event = threading.Event()
        self._last_hash: Optional[str] = None

    def start(self, blocking: bool = False) -> Optional[threading.Thread]:
        if blocking:
            self.run_forever()
            return None

        thread = threading.Thread(
            target=self.run_forever,
            name='ClipboardCollector',
            daemon=True,
        )
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()

    def run_forever(self) -> None:
        logger.info('ClipboardCollector started.')

        try:
            while not self._stop_event.is_set():
                try:
                    self.poll_once()
                except Exception:
                    logger.exception('ClipboardCollector poll failed.')

                self._stop_event.wait(self.poll_interval_sec)

        finally:
            self._close_store()
            logger.info('ClipboardCollector stopped.')

    def poll_once(self) -> None:
        text = read_clipboard_text()

        if text is None:
            return

        if len(text) < self.min_text_chars:
            return

        if len(text) > self.max_text_chars:
            # MVP 阶段直接截断,避免把超长日志\网页正文\JSON 全部写入库
            text = text[: self.max_text_chars]

        content_hash = make_content_hash(text)

        # 避免同一轮运行期间, 每秒反复 upsert 同一条剪贴板内容
        if content_hash == self._last_hash:
            return

        self._last_hash = content_hash

        now = datetime.now()
        is_sensitive, sensitivity_reason = detect_sensitive(text)
        if not is_sensitive:
            is_sensitive, sensitivity_reason = self.detect_sensitive_keyword(text)

        content_preview = make_preview(text, self.preview_chars)
        entry = ClipboardEntryState(
            id=None,
            date=now.date().isoformat(),
            first_seen_at=now,
            last_seen_at=now,
            content=content_preview if self.clipboard_preview_only else text,
            content_preview=content_preview,
            content_hash=content_hash,
            char_count=len(text),
            is_sensitive=is_sensitive,
            sensitivity_reason=sensitivity_reason,
            is_selected=(not is_sensitive) if self.sensitive_unselected_by_default else True,
        )

        entry.id = self.store.save_entry(entry)

        logger.info(
            'Saved clipboard entry id=%s chars=%s sensitive=%s preview=%s',
            entry.id,
            entry.char_count,
            entry.is_sensitive,
            entry.content_preview,
        )

    def _close_store(self) -> None:
        close = getattr(self.store, 'close', None)
        if callable(close):
            close()

    def detect_sensitive_keyword(self, text: str) -> tuple[bool, Optional[str]]:
        lower_text = text.lower()
        for keyword in self.sensitive_keywords:
            if keyword.lower() in lower_text:
                return True, f'keyword:{keyword}'
        return False, None
