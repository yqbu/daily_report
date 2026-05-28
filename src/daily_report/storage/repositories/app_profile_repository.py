from __future__ import annotations

import base64
import binascii
import mimetypes
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from daily_report.config.paths import get_runtime_paths
from daily_report.service.category import infer_category_for_app


DEFAULT_APP_CATEGORY_COLORS: tuple[tuple[str, str, int], ...] = (
    ('开发编码', '#2563EB', 10),
    ('问题排查', '#DC2626', 20),
    ('资料调研', '#0891B2', 30),
    ('AI 辅助', '#7C3AED', 40),
    ('文档整理', '#16A34A', 50),
    ('沟通协作', '#D97706', 60),
    ('系统配置', '#64748B', 70),
    ('其他', '#8F98A8', 1000),
)

DEFAULT_CATEGORY_NAME = '其他'
_HEX_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
_APP_ICON_DATA_URL_RE = re.compile(r'^data:([^;,]*);base64,(.+)$', re.DOTALL)
_APP_ICON_EXTENSIONS = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
    'image/x-icon': 'ico',
    'image/vnd.microsoft.icon': 'ico',
}
_APP_ICON_MIME_BY_EXTENSION = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'ico': 'image/x-icon',
}
_MAX_APP_ICON_BYTES = 1024 * 1024


class AppProfileRepository:
    """Repository for per-application display and classification settings."""

    def __init__(self, conn: sqlite3.Connection, icon_dir: str | Path | None = None):
        self.conn = conn
        self.icon_dir = Path(icon_dir) if icon_dir is not None else get_runtime_paths().data_dir / 'app_icons'
        self.data_dir = self.icon_dir.parent

    def ensure_default_categories(self) -> None:
        now = _now()
        for name, color, sort_order in DEFAULT_APP_CATEGORY_COLORS:
            self.conn.execute(
                """
                INSERT INTO app_categories (
                    name, color, sort_order, is_builtin, is_deleted, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, 0, ?, ?)
                ON CONFLICT(name) DO NOTHING
                """,
                (name, color, sort_order, now, now),
            )
        self.conn.commit()

    def list_categories(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        self.ensure_default_categories()
        clauses = []
        params: list[Any] = []
        if not include_deleted:
            clauses.append('is_deleted = 0')
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        rows = self.conn.execute(
            f"""
            SELECT c.*,
                   COALESCE(p.profile_count, 0) AS profile_count
            FROM app_categories c
            LEFT JOIN (
                SELECT category, COUNT(*) AS profile_count
                FROM app_profiles
                WHERE category IS NOT NULL AND category <> ''
                GROUP BY category
            ) p ON p.category = c.name
            {where}
            ORDER BY c.sort_order ASC, c.name ASC
            """,
            tuple(params),
        ).fetchall()
        return [_category_dict(row) for row in rows]

    def save_category(
        self,
        *,
        name: str,
        color: str | None = None,
        sort_order: int | None = None,
    ) -> dict[str, Any]:
        self.ensure_default_categories()
        normalized_name = _normalize_text(name)
        if not normalized_name:
            raise ValueError('Category name is required.')

        existing = self.get_category(normalized_name, include_deleted=True)
        normalized_color = normalize_color(color, fallback=existing.get('color') if existing else '#8F98A8')
        now = _now()
        if existing:
            next_sort_order = int(sort_order if sort_order is not None else existing.get('sort_order') or 100)
            self.conn.execute(
                """
                UPDATE app_categories
                SET color = ?,
                    sort_order = ?,
                    is_deleted = 0,
                    updated_at = ?
                WHERE name = ?
                """,
                (normalized_color, next_sort_order, now, normalized_name),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO app_categories (
                    name, color, sort_order, is_builtin, is_deleted, created_at, updated_at
                )
                VALUES (?, ?, ?, 0, 0, ?, ?)
                """,
                (normalized_name, normalized_color, int(sort_order or 100), now, now),
            )
        self.conn.commit()
        row = self.get_category(normalized_name, include_deleted=True)
        if row is None:
            raise RuntimeError(f'Failed to save app category: {normalized_name}')
        return row

    def delete_category(
        self,
        name: str,
        *,
        fallback_category: str = DEFAULT_CATEGORY_NAME,
    ) -> dict[str, Any]:
        self.ensure_default_categories()
        normalized_name = _normalize_text(name)
        if not normalized_name:
            raise ValueError('Category name is required.')
        if normalized_name == fallback_category:
            raise ValueError(f'Cannot delete fallback category: {fallback_category}')

        fallback = self.get_category(fallback_category)
        if fallback is None:
            self.save_category(name=fallback_category, color='#8F98A8', sort_order=1000)

        now = _now()
        self.conn.execute(
            """
            UPDATE app_categories
            SET is_deleted = 1,
                updated_at = ?
            WHERE name = ?
            """,
            (now, normalized_name),
        )
        self.conn.execute(
            """
            UPDATE app_profiles
            SET category = ?,
                updated_at = ?
            WHERE category = ?
            """,
            (fallback_category, now, normalized_name),
        )
        self.conn.commit()
        return {'name': normalized_name, 'deleted': True, 'fallback_category': fallback_category}

    def get_category(self, name: str, include_deleted: bool = False) -> dict[str, Any] | None:
        clauses = ['name = ?']
        params: list[Any] = [_normalize_text(name)]
        if not include_deleted:
            clauses.append('is_deleted = 0')
        row = self.conn.execute(
            f"""
            SELECT *
            FROM app_categories
            WHERE {' AND '.join(clauses)}
            """,
            tuple(params),
        ).fetchone()
        return _category_dict(row) if row else None

    def list_profiles(
        self,
        *,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 100,
        include_unobserved: bool = True,
    ) -> dict[str, Any]:
        self.ensure_default_categories()
        filters = filters or {}
        categories = self.list_categories()
        category_colors = {str(category['name']): str(category['color']) for category in categories}
        observed = self._observed_app_rows()
        profiles = {str(row['app_key']): dict(row) for row in self._profile_rows()}

        items = [
            self._merge_profile(
                observed_row=dict(row),
                profile=profiles.pop(str(row['app_key']), None),
                category_colors=category_colors,
            )
            for row in observed
        ]
        if include_unobserved:
            for profile in profiles.values():
                items.append(self._merge_profile(observed_row=None, profile=profile, category_colors=category_colors))

        count_filters = {**filters, 'classification': 'all'}
        counts = _profile_counts(self._filter_profiles(items, count_filters))
        items = self._filter_profiles(items, filters)
        _sort_profiles(items, filters)

        page = max(1, int(page or 1))
        page_size = max(1, min(500, int(page_size or 100)))
        start = (page - 1) * page_size
        paged = items[start:start + page_size]
        return {
            'items': paged,
            'total': len(items),
            'page': page,
            'page_size': page_size,
            'counts': counts,
            'categories': categories,
        }

    def get_profile(self, app_key: str) -> dict[str, Any] | None:
        normalized_key = normalize_app_key(app_key)
        if not normalized_key:
            return None
        row = self.conn.execute(
            """
            SELECT *
            FROM app_profiles
            WHERE app_key = ?
            """,
            (normalized_key,),
        ).fetchone()
        return _profile_dict(row) if row else None

    def save_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_default_categories()
        existing = self.get_profile(_app_key_from_payload(payload))
        merged = _merge_profile_payload(existing, payload)
        if not merged['app_key']:
            raise ValueError('app_key or process_name is required.')

        category = _normalize_text(merged.get('category'))
        if category:
            if self.get_category(category) is None:
                self.save_category(name=category, color=None, sort_order=500)
        else:
            category = None

        color = normalize_color(merged.get('color'), fallback=None)
        icon_path = self._resolve_icon_path(merged, existing)
        icon_base64 = None if icon_path else _normalize_optional_text(merged.get('icon_base64'))
        now = _now()
        self.conn.execute(
            """
            INSERT INTO app_profiles (
                app_key, process_name, exe_path, display_name, category, color, icon_base64, icon_path,
                track_enabled, capture_title_enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(app_key) DO UPDATE SET
                process_name = excluded.process_name,
                exe_path = excluded.exe_path,
                display_name = excluded.display_name,
                category = excluded.category,
                color = excluded.color,
                icon_base64 = excluded.icon_base64,
                icon_path = excluded.icon_path,
                track_enabled = excluded.track_enabled,
                capture_title_enabled = excluded.capture_title_enabled,
                updated_at = excluded.updated_at
            """,
            (
                merged['app_key'],
                merged['process_name'],
                merged.get('exe_path'),
                _normalize_optional_text(merged.get('display_name')),
                category,
                color,
                icon_base64,
                icon_path,
                int(bool(merged.get('track_enabled', True))),
                int(bool(merged.get('capture_title_enabled', True))),
                existing.get('created_at') if existing else now,
                now,
            ),
        )
        self.conn.commit()
        observed = self._observed_app_row(merged['app_key'])
        profile = self.get_profile(merged['app_key'])
        if profile is None:
            raise RuntimeError(f'Failed to save app profile: {merged["app_key"]}')
        return self._merge_profile(observed_row=observed, profile=profile)

    def reset_profile(self, app_key: str) -> dict[str, Any]:
        normalized_key = normalize_app_key(app_key)
        if not normalized_key:
            raise ValueError('app_key is required.')
        existing = self.get_profile(normalized_key)
        self._delete_icon_file(existing.get('icon_path') if existing else None)
        self.conn.execute('DELETE FROM app_profiles WHERE app_key = ?', (normalized_key,))
        self.conn.commit()
        observed = self._observed_app_row(normalized_key)
        return self._merge_profile(observed_row=observed, profile=None)

    def delete_app_records(
        self,
        app_key: str,
        *,
        target_date: str | None = None,
        hard_delete: bool = False,
    ) -> dict[str, Any]:
        normalized_key = normalize_app_key(app_key)
        if not normalized_key:
            raise ValueError('app_key is required.')

        clauses = ['LOWER(TRIM(process_name)) = ?']
        params: list[Any] = [normalized_key]
        if target_date:
            clauses.append('date = ?')
            params.append(target_date)
        if hard_delete:
            sql = f"DELETE FROM app_sessions WHERE {' AND '.join(clauses)}"
            cursor = self.conn.execute(sql, tuple(params))
        else:
            clauses.append('is_deleted = 0')
            cursor = self.conn.execute(
                f"""
                UPDATE app_sessions
                SET is_deleted = 1,
                    updated_at = ?
                WHERE {' AND '.join(clauses)}
                """,
                tuple([_now(), *params]),
            )
        self.conn.commit()
        return {'app_key': normalized_key, 'deleted_count': int(cursor.rowcount or 0)}

    def resolve_app_metadata(
        self,
        *,
        process_name: str | None,
        app_name: str | None = None,
        exe_path: str | None = None,
        window_title: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_default_categories()
        app_key = normalize_app_key(process_name, exe_path)
        profile = self.get_profile(app_key) if app_key else None
        inferred_category = infer_category_for_app(process_name, window_title)
        category = _normalize_optional_text(profile.get('category') if profile else None) or inferred_category
        category_row = self.get_category(category) or self.get_category(DEFAULT_CATEGORY_NAME)
        category_color = str((category_row or {}).get('color') or '#8F98A8')
        color = _normalize_optional_text(profile.get('color') if profile else None) or category_color
        display_name = (
            _normalize_optional_text(profile.get('display_name') if profile else None)
            or _normalize_optional_text(app_name)
            or _normalize_optional_text(process_name)
            or app_key
        )
        return {
            'app_key': app_key,
            'display_name': display_name,
            'category': category,
            'color': color,
            'track_enabled': bool(profile.get('track_enabled', 1)) if profile else True,
            'capture_title_enabled': bool(profile.get('capture_title_enabled', 1)) if profile else True,
            'profile': profile,
        }

    def _profile_rows(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT *
                FROM app_profiles
                ORDER BY updated_at DESC, app_key ASC
                """
            ).fetchall()
        )

    def _observed_app_rows(self) -> list[sqlite3.Row]:
        week_start, week_end = _current_week_bounds()
        return list(
            self.conn.execute(
                """
                SELECT
                    LOWER(TRIM(process_name)) AS app_key,
                    MAX(process_name) AS process_name,
                    MAX(app_name) AS default_display_name,
                    MAX(exe_path) AS exe_path,
                    MAX(window_title) AS sample_window_title,
                    MAX(start_time) AS last_seen_at,
                    COUNT(*) AS session_count,
                    COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
                    COALESCE(SUM(active_duration_sec), 0) AS total_active_duration_sec
                FROM app_sessions
                WHERE process_name IS NOT NULL
                  AND TRIM(process_name) <> ''
                  AND is_deleted = 0
                  AND date BETWEEN ? AND ?
                GROUP BY LOWER(TRIM(process_name))
                """,
                (week_start, week_end),
            ).fetchall()
        )

    def _observed_app_row(self, app_key: str) -> dict[str, Any] | None:
        normalized_key = normalize_app_key(app_key)
        if not normalized_key:
            return None
        week_start, week_end = _current_week_bounds()
        row = self.conn.execute(
            """
            SELECT
                LOWER(TRIM(process_name)) AS app_key,
                MAX(process_name) AS process_name,
                MAX(app_name) AS default_display_name,
                MAX(exe_path) AS exe_path,
                MAX(window_title) AS sample_window_title,
                MAX(start_time) AS last_seen_at,
                COUNT(*) AS session_count,
                COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
                COALESCE(SUM(active_duration_sec), 0) AS total_active_duration_sec
            FROM app_sessions
            WHERE LOWER(TRIM(process_name)) = ?
              AND is_deleted = 0
              AND date BETWEEN ? AND ?
            GROUP BY LOWER(TRIM(process_name))
            """,
            (normalized_key, week_start, week_end),
        ).fetchone()
        return dict(row) if row else None

    def _merge_profile(
        self,
        *,
        observed_row: dict[str, Any] | None,
        profile: dict[str, Any] | None,
        category_colors: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        observed_row = observed_row or {}
        profile = profile or {}
        app_key = str(profile.get('app_key') or observed_row.get('app_key') or '')
        process_name = str(profile.get('process_name') or observed_row.get('process_name') or app_key)
        default_display_name = str(observed_row.get('default_display_name') or process_name)
        sample_window_title = str(observed_row.get('sample_window_title') or '')
        inferred_category = infer_category_for_app(process_name, sample_window_title)
        category = _normalize_optional_text(profile.get('category')) or inferred_category
        category_color = self._category_color(category, category_colors)
        manual_color = normalize_color(profile.get('color'), fallback=None)
        effective_color = manual_color or category_color
        display_name = _normalize_optional_text(profile.get('display_name')) or default_display_name
        track_enabled = bool(profile.get('track_enabled', 1))
        capture_title_enabled = bool(profile.get('capture_title_enabled', 1))

        return {
            'app_key': app_key,
            'process_name': process_name,
            'exe_path': profile.get('exe_path') or observed_row.get('exe_path'),
            'default_display_name': default_display_name,
            'display_name': _normalize_optional_text(profile.get('display_name')),
            'effective_display_name': display_name,
            'category': category,
            'category_color': category_color,
            'color': manual_color,
            'effective_color': effective_color,
            'icon_base64': profile.get('icon_base64'),
            'icon_path': _normalize_optional_text(profile.get('icon_path')),
            'icon_url': self._icon_url(profile.get('icon_path')),
            'track_enabled': track_enabled,
            'capture_title_enabled': capture_title_enabled,
            'session_count': int(observed_row.get('session_count') or 0),
            'total_duration_sec': float(observed_row.get('total_duration_sec') or 0),
            'total_active_duration_sec': float(observed_row.get('total_active_duration_sec') or 0),
            'last_seen_at': observed_row.get('last_seen_at'),
            'sample_window_title': sample_window_title,
            'is_configured': bool(profile),
            'is_classified': category != DEFAULT_CATEGORY_NAME,
            'created_at': profile.get('created_at'),
            'updated_at': profile.get('updated_at'),
        }

    def _category_color(self, category: str, category_colors: dict[str, str] | None = None) -> str:
        if category_colors is not None:
            return category_colors.get(category) or category_colors.get(DEFAULT_CATEGORY_NAME) or '#8F98A8'

        category_row = self.get_category(category) or self.get_category(DEFAULT_CATEGORY_NAME)
        return str((category_row or {}).get('color') or '#8F98A8')

    def _resolve_icon_path(self, merged: dict[str, Any], existing: dict[str, Any] | None) -> str | None:
        icon_data_url = _normalize_optional_text(merged.get('icon_data_url') or merged.get('iconDataUrl'))
        existing_path = _normalize_optional_text(existing.get('icon_path') if existing else None)
        explicit_path = _normalize_optional_text(merged.get('icon_path') or merged.get('iconPath'))
        if not icon_data_url:
            return explicit_path or existing_path

        return self._save_icon_file(
            app_key=str(merged.get('app_key') or ''),
            data_url=icon_data_url,
            file_name=_normalize_optional_text(merged.get('icon_file_name') or merged.get('iconFileName')),
            existing_path=existing_path,
        )

    def _save_icon_file(
        self,
        *,
        app_key: str,
        data_url: str,
        file_name: str | None,
        existing_path: str | None,
    ) -> str:
        match = _APP_ICON_DATA_URL_RE.match(data_url)
        if match is None:
            raise ValueError('Invalid app icon payload.')

        mime_type = match.group(1).lower()
        extension = _APP_ICON_EXTENSIONS.get(mime_type) or _icon_extension_from_file_name(file_name)
        if extension is None:
            raise ValueError(f'Unsupported app icon type: {mime_type}')

        try:
            icon_bytes = base64.b64decode(match.group(2), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError('Invalid app icon base64 data.') from exc
        if len(icon_bytes) > _MAX_APP_ICON_BYTES:
            raise ValueError('App icon file is too large.')

        relative_path = existing_path or f'app_icons/{_safe_icon_file_stem(app_key or file_name or "app")}.{extension}'
        icon_path = self._resolve_relative_icon_path(relative_path)
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        icon_path.write_bytes(icon_bytes)
        return icon_path.relative_to(self.data_dir.resolve()).as_posix()

    def _delete_icon_file(self, icon_path: Any) -> None:
        normalized_path = _normalize_optional_text(icon_path)
        if not normalized_path:
            return
        try:
            resolved_path = self._resolve_relative_icon_path(normalized_path)
        except ValueError:
            return
        if resolved_path.exists() and resolved_path.is_file():
            resolved_path.unlink()

    def _resolve_relative_icon_path(self, icon_path: str) -> Path:
        data_dir = self.data_dir.resolve()
        resolved_path = (data_dir / icon_path).resolve()
        if data_dir != resolved_path and data_dir not in resolved_path.parents:
            raise ValueError('Invalid app icon path.')
        return resolved_path

    def _icon_url(self, icon_path: Any) -> str | None:
        normalized_path = _normalize_optional_text(icon_path)
        if not normalized_path:
            return None
        try:
            resolved_path = self._resolve_relative_icon_path(normalized_path)
        except ValueError:
            return None
        if not resolved_path.exists() or not resolved_path.is_file():
            return None

        extension = resolved_path.suffix.lower().lstrip('.')
        mime_type = _APP_ICON_MIME_BY_EXTENSION.get(extension) or mimetypes.guess_type(resolved_path.name)[0]
        if not mime_type:
            return None
        return f'data:{mime_type};base64,{base64.b64encode(resolved_path.read_bytes()).decode("ascii")}'

    @staticmethod
    def _filter_profiles(items: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
        keyword = str(filters.get('keyword') or '').strip().lower()
        category = _normalize_optional_text(filters.get('category'))
        classification = str(filters.get('classification') or 'all').strip().lower()
        track_enabled = _optional_bool(filters.get('track_enabled'))

        def keep(item: dict[str, Any]) -> bool:
            if keyword:
                haystack = ' '.join(
                    str(item.get(key) or '')
                    for key in ('app_key', 'process_name', 'effective_display_name', 'default_display_name')
                ).lower()
                if keyword not in haystack:
                    return False
            if category and item.get('category') != category:
                return False
            if classification in {'unclassified', 'other'} and item.get('is_classified'):
                return False
            if classification == 'classified' and not item.get('is_classified'):
                return False
            if classification == 'configured' and not item.get('is_configured'):
                return False
            if track_enabled is not None and bool(item.get('track_enabled')) != track_enabled:
                return False
            return True

        return [item for item in items if keep(item)]


def normalize_app_key(value: str | None, exe_path: str | None = None) -> str:
    text = _normalize_text(value)
    if not text and exe_path:
        text = _normalize_text(exe_path)
    if not text:
        return ''
    text = text.replace('\\', '/').rsplit('/', 1)[-1]
    return text.lower()


def normalize_color(value: Any, fallback: str | None = None) -> str | None:
    text = _normalize_text(value)
    if not text:
        return fallback
    normalized = text if text.startswith('#') else f'#{text}'
    if not _HEX_COLOR_RE.match(normalized):
        return fallback
    return normalized.upper()


def _app_key_from_payload(payload: dict[str, Any]) -> str:
    return normalize_app_key(
        str(payload.get('app_key') or payload.get('process_name') or ''),
        str(payload.get('exe_path') or '') or None,
    )


def _merge_profile_payload(
    existing: dict[str, Any] | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    app_key = _app_key_from_payload(payload)
    process_name = _normalize_text(payload.get('process_name')) or app_key
    result = {
        'app_key': app_key,
        'process_name': process_name,
        'exe_path': existing.get('exe_path') if existing else None,
        'display_name': existing.get('display_name') if existing else None,
        'category': existing.get('category') if existing else None,
        'color': existing.get('color') if existing else None,
        'icon_base64': existing.get('icon_base64') if existing else None,
        'icon_path': existing.get('icon_path') if existing else None,
        'track_enabled': existing.get('track_enabled', True) if existing else True,
        'capture_title_enabled': existing.get('capture_title_enabled', True) if existing else True,
    }
    for key in (
        'exe_path',
        'display_name',
        'category',
        'color',
        'icon_base64',
        'icon_path',
        'icon_data_url',
        'iconDataUrl',
        'icon_file_name',
        'iconFileName',
        'track_enabled',
        'capture_title_enabled',
    ):
        if key in payload:
            result[key] = payload[key]
    return result


def _category_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data['is_builtin'] = bool(data.get('is_builtin'))
    data['is_deleted'] = bool(data.get('is_deleted'))
    data['profile_count'] = int(data.get('profile_count') or 0)
    return data


def _profile_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data['track_enabled'] = bool(data.get('track_enabled'))
    data['capture_title_enabled'] = bool(data.get('capture_title_enabled'))
    return data


def _profile_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        'all': len(items),
        'classified': sum(1 for item in items if item.get('is_classified')),
        'unclassified': sum(1 for item in items if not item.get('is_classified')),
        'configured': sum(1 for item in items if item.get('is_configured')),
        'excluded': sum(1 for item in items if not item.get('track_enabled')),
    }


def _sort_profiles(items: list[dict[str, Any]], filters: dict[str, Any]) -> None:
    sort_by = str(filters.get('sort_by') or filters.get('sortBy') or 'last_seen').strip().lower()
    sort_direction = str(filters.get('sort_direction') or filters.get('sortDirection') or '').strip().lower()
    if sort_by not in {'last_seen', 'name', 'duration', 'session_count'}:
        sort_by = 'last_seen'
    if sort_direction not in {'asc', 'desc'}:
        sort_direction = 'asc' if sort_by == 'name' else 'desc'

    def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        name = str(item.get('effective_display_name') or item.get('default_display_name') or item.get('process_name') or '')
        app_key = str(item.get('app_key') or '')
        if sort_by == 'name':
            return (name.casefold(), app_key)
        if sort_by == 'duration':
            return (float(item.get('total_active_duration_sec') or 0), name.casefold(), app_key)
        if sort_by == 'session_count':
            return (int(item.get('session_count') or 0), name.casefold(), app_key)
        return (
            str(item.get('last_seen_at') or ''),
            float(item.get('total_active_duration_sec') or 0),
            name.casefold(),
            app_key,
        )

    items.sort(key=sort_key, reverse=sort_direction == 'desc')


def _current_week_bounds() -> tuple[str, str]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start.isoformat(), week_end.isoformat()


def _safe_icon_file_stem(value: str) -> str:
    normalized = normalize_app_key(value) or 'app'
    return re.sub(r'[^a-zA-Z0-9_.-]+', '_', normalized).strip('._') or 'app'


def _icon_extension_from_file_name(file_name: str | None) -> str | None:
    suffix = Path(file_name or '').suffix.lower().lstrip('.')
    if suffix == 'jpeg':
        suffix = 'jpg'
    return suffix if suffix in {'png', 'jpg', 'webp', 'ico'} else None


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {'true', '1', 'yes', 'included', 'enabled'}:
        return True
    if text in {'false', '0', 'no', 'excluded', 'disabled'}:
        return False
    return None


def _normalize_optional_text(value: Any) -> str | None:
    text = _normalize_text(value)
    return text or None


def _normalize_text(value: Any) -> str:
    return str(value or '').replace('\x00', '').strip()


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
