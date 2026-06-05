from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.storage.database import create_connection, default_db_path, init_database


@dataclass(frozen=True)
class RawEvent:
    source_type: str
    source_id: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class TimelineEvent:
    event_id: str
    source_type: str
    source_id: int
    start_time: str
    end_time: str | None
    title: str
    subtitle: str
    content_preview: str
    category: str
    is_selected: bool
    is_sensitive: bool
    is_deleted: bool
    source_ids: list[int] | None = None
    item_count: int = 1
    aggregate_kind: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop('raw', None)
        return data


class SourceAdapter(ABC):
    source_type: str

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()

    @abstractmethod
    def list_raw_by_date(
        self,
        date: str,
        selected: bool | None = None,
        sensitive: bool | None = None,
        keyword: str | None = None,
        include_deleted: bool = False,
        limit: int = 500,
        offset: int = 0,
    ) -> list[RawEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_raw_detail(self, source_id: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        raise NotImplementedError

    @abstractmethod
    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        raise NotImplementedError

    @abstractmethod
    def update_selected(self, source_id: int, selected: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_deleted(self, source_id: int, deleted: bool) -> None:
        raise NotImplementedError

    def _connect(self) -> sqlite3.Connection:
        conn = create_connection(self.db_path)
        init_database(conn)
        return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def row_get(row: sqlite3.Row | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(row, sqlite3.Row):
        return row[key] if key in row.keys() else default
    return row.get(key, default)


def optional_text(row: sqlite3.Row | dict[str, Any], key: str) -> str | None:
    value = str(row_get(row, key, '') or '').strip()
    return value or None


def row_bool(row: sqlite3.Row | dict[str, Any], key: str, default: bool) -> bool:
    value = row_get(row, key, int(default))
    if value is None:
        value = int(default)
    return bool(value)


def hhmm(value: Any) -> str:
    text = str(value or '')
    if len(text) >= 16 and text[10] in {' ', 'T'}:
        return text[11:16]
    return text[:5]


def format_seconds(value: float) -> str:
    seconds = int(value or 0)
    hours, rem = divmod(seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f'{hours}h{minutes:02d}m'
    if minutes:
        return f'{minutes}m'
    return f'{seconds}s'


def limit_clause(limit: int | None) -> str:
    return 'LIMIT ? OFFSET ?' if limit is not None else ''


def with_limit(params: list[Any], limit: int | None, offset: int = 0) -> list[Any]:
    if limit is None:
        return params
    return [*params, max(1, int(limit)), max(0, int(offset or 0))]
