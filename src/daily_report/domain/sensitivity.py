from __future__ import annotations

import hashlib
import re

SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("password", re.compile(r"\b(pass(word)?|pwd)\s*[:=]\s*\S{6,}", re.IGNORECASE)),
    ("password", re.compile(r"\bpassword\b", re.IGNORECASE)),
    ("api_key", re.compile(r"\b(api[_-]?key|access[_-]?token|secret)\s*[:=]\s*\S{8,}", re.IGNORECASE)),
    ("api_key", re.compile(r"\bapi\s*[_-]?\s*key\b|\baccess\s*token\b|\bsecret\b", re.IGNORECASE)),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


def hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def make_preview(text: str, max_chars: int = 120) -> str:
    preview = re.sub(r"\s+", " ", str(text or "")).strip()
    if max_chars <= 0 or len(preview) <= max_chars:
        return preview
    return preview[:max_chars].rstrip()


def detect_sensitive_text(text: str) -> tuple[bool, str | None]:
    value = str(text or "")
    for reason, pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            return True, reason
    return False, None
