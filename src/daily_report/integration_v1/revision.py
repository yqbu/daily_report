from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def stable_revision(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value)).hexdigest()
    return f"{prefix}-{digest}"


def stable_etag(resource_key: str, revision: str) -> str:
    digest = hashlib.sha256(
        canonical_json({"resource": resource_key, "revision": revision})
    ).hexdigest()
    return f'"{digest}"'
