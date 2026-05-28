from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from daily_report.storage.database import create_connection, default_db_path, init_database
from daily_report.storage.repositories.app_profile_repository import AppProfileRepository


class AppProfileService:
    """JSON-friendly application configuration service for the desktop UI."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.icon_dir = self.db_path.parent / 'app_icons'

    def list_profiles(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        filters = params.get('filters') if isinstance(params.get('filters'), dict) else {}
        with self._connect() as conn:
            return self._repository(conn).list_profiles(
                filters=filters,
                page=int(params.get('page') or 1),
                page_size=int(params.get('page_size') or params.get('pageSize') or 100),
                include_unobserved=bool(
                    params.get('include_unobserved', params.get('includeUnobserved', True))
                ),
            )

    def save_profile(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            return self._repository(conn).save_profile(payload or {})

    def reset_profile(self, payload: dict[str, Any] | str | None = None) -> dict[str, Any]:
        app_key = _app_key_arg(payload)
        with self._connect() as conn:
            return self._repository(conn).reset_profile(app_key)

    def delete_app_records(self, payload: dict[str, Any] | str | None = None) -> dict[str, Any]:
        app_key = _app_key_arg(payload)
        target_date = payload.get('date') if isinstance(payload, dict) else None
        hard_delete = bool(payload.get('hard_delete') or payload.get('hardDelete')) if isinstance(payload, dict) else False
        with self._connect() as conn:
            return self._repository(conn).delete_app_records(
                app_key,
                target_date=str(target_date or '').strip() or None,
                hard_delete=hard_delete,
            )

    def list_categories(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        include_deleted = bool((payload or {}).get('include_deleted') or (payload or {}).get('includeDeleted'))
        with self._connect() as conn:
            categories = self._repository(conn).list_categories(include_deleted=include_deleted)
            return {'items': categories, 'total': len(categories)}

    def save_category(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        with self._connect() as conn:
            return self._repository(conn).save_category(
                name=str(payload.get('name') or ''),
                color=str(payload.get('color') or '') or None,
                sort_order=int(payload.get('sort_order') or payload.get('sortOrder') or 100),
            )

    def delete_category(self, payload: dict[str, Any] | str | None = None) -> dict[str, Any]:
        if isinstance(payload, dict):
            name = str(payload.get('name') or '')
            fallback = str(payload.get('fallback_category') or payload.get('fallbackCategory') or '其他')
        else:
            name = str(payload or '')
            fallback = '其他'
        with self._connect() as conn:
            return self._repository(conn).delete_category(name, fallback_category=fallback)

    def _repository(self, conn: sqlite3.Connection) -> AppProfileRepository:
        return AppProfileRepository(conn, icon_dir=self.icon_dir)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = create_connection(self.db_path)
        try:
            init_database(conn)
            yield conn
        finally:
            conn.close()


def _app_key_arg(payload: dict[str, Any] | str | None) -> str:
    if isinstance(payload, dict):
        return str(payload.get('app_key') or payload.get('appKey') or payload.get('process_name') or '')
    return str(payload or '')
