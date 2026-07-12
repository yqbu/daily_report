from __future__ import annotations

import hashlib
import re

SENSITIVE_KEYWORDS = (
    'password',
    'passwd',
    'pwd',
    'token',
    'api_key',
    'apikey',
    'secret',
    'cookie',
    'authorization',
    'bearer',
    'access_key',
    'private_key',
    '密码',
    '密钥',
    '令牌',
    '验证码',
    '身份证',
    '银行卡',
    '手机号',
    '邮箱',
)

SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ('private_key', re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', re.I)),
    ('password', re.compile(r'\b(password|passwd|pwd)\b\s*[:=]\s*[^\s\'"]{4,}', re.I)),
    (
        'token',
        re.compile(
            r'\b(token|api[_-]?key|apikey|secret|access[_-]?key|authorization|cookie)\b'
            r'\s*[:=]\s*[^\s\'"]{8,}',
            re.I,
        ),
    ),
    ('bearer', re.compile(r'\bbearer\s+[A-Za-z0-9._~+/=-]{20,}', re.I)),
    ('jwt', re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b')),
    ('email', re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')),
    ('phone_number', re.compile(r'(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)')),
    ('id_card', re.compile(r'(?<!\d)\d{17}[\dXx](?!\d)')),
    ('bank_card', re.compile(r'(?<!\d)(?:\d[ -]?){15,19}(?!\d)')),
    ('possible_secret_token', re.compile(r'(?<![A-Za-z0-9])[A-Za-z0-9_./+=:-]{32,}(?![A-Za-z0-9])')),
)


def detect_sensitive_text(text: str) -> tuple[bool, str | None]:
    value = str(text or '')
    if not value.strip():
        return False, None

    lower_value = value.lower()
    for keyword in SENSITIVE_KEYWORDS:
        if keyword.lower() in lower_value:
            return True, f'keyword:{keyword}'

    for reason, pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            return True, reason

    return False, None


def make_preview(text: str, max_len: int = 120) -> str:
    preview = re.sub(r'\s+', ' ', str(text or '').replace('\x00', '')).strip()
    if len(preview) <= max_len:
        return preview
    return preview[: max(0, max_len - 3)] + '...'


def hash_text(text: str) -> str:
    return hashlib.sha256(str(text or '').encode('utf-8', errors='ignore')).hexdigest()
