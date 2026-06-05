from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MaterialCard:
    source_type: str
    source_id: int
    time_range: str
    category: str
    title: str
    summary: str
    evidence: str
    importance: int
    is_sensitive: bool
    record_type: str | None = None
    entry_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
