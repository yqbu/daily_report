from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator
from typing import Optional

from daily_report.config.paths import get_runtime_paths

logger = logging.getLogger(__name__)
_WAL_CONFIGURED_PATHS: set[Path] = set()
_INITIALIZED_DATABASE_PATHS: set[Path] = set()

# def default_db_path() -> Path:
#     """
#     默认数据库路径:
#     Windows 下默认放到 %APPDATA%/daily-report/daily_report.db
#     """
#     appdata = os.getenv("APPDATA")
#
#     if appdata:
#         return Path(appdata) / "daily-report" / "daily_report.db"
#
#     return Path.home() / ".daily-report" / "daily_report.db"


# def default_db_path() -> Path:
#     project_root = Path(__file__).resolve().parents[3]
#     data_dir = project_root / 'data'
#
#     return data_dir / 'daily_report.db'

def default_db_path() -> Path:
    return get_runtime_paths().db_path


def create_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """
    创建 SQLite 连接
    """
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=True)
    conn.row_factory = sqlite3.Row

    # 推荐开启 WAL, 读写并发会更友好
    # WAL is persistent per database file, so avoid re-negotiating it on every short-lived GUI query.
    resolved_path = path.resolve()
    if resolved_path not in _WAL_CONFIGURED_PATHS:
        conn.execute('PRAGMA journal_mode=WAL;')
        _WAL_CONFIGURED_PATHS.add(resolved_path)

    # 外键支持, 后面如果加关联表会有用
    conn.execute('PRAGMA foreign_keys=ON;')

    conn.execute('PRAGMA synchronous = NORMAL;')
    conn.execute('PRAGMA busy_timeout = 5000;')

    return conn


def init_database(conn: sqlite3.Connection, schema_path: str | Path | None = None) -> None:
    """
    初始化数据库表结构
    """
    cache_key = _connection_database_path(conn) if schema_path is None else None
    if cache_key is not None and cache_key in _INITIALIZED_DATABASE_PATHS:
        return

    if schema_path is None:
        schema_path = Path(__file__).with_name('schema.sql')

    schema_sql = _read_schema_sql(str(Path(schema_path).resolve()))

    _run_pre_schema_migrations(conn)
    conn.executescript(schema_sql)
    _run_safe_migrations(conn)
    conn.commit()
    if cache_key is not None:
        _INITIALIZED_DATABASE_PATHS.add(cache_key)


@lru_cache(maxsize=4)
def _read_schema_sql(schema_path: str) -> str:
    return Path(schema_path).read_text(encoding='utf-8')


def _connection_database_path(conn: sqlite3.Connection) -> Path | None:
    try:
        row = conn.execute("PRAGMA database_list").fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None

    filename = row["file"] if isinstance(row, sqlite3.Row) else row[2]
    if not filename:
        return None
    return Path(str(filename)).resolve()


def _run_pre_schema_migrations(conn: sqlite3.Connection) -> None:
    """Add columns needed by schema indexes before executing CREATE INDEX statements."""
    _ensure_columns(
        conn,
        'app_sessions',
        {
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
        },
    )
    _ensure_columns(
        conn,
        'browser_history_entries',
        {
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
        },
    )
    _ensure_columns(
        conn,
        'clipboard_entries',
        {
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
            'is_sensitive': 'INTEGER NOT NULL DEFAULT 0',
        },
    )
    _ensure_columns(
        conn,
        'ai_prompt_entries',
        {
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_sensitive': 'INTEGER NOT NULL DEFAULT 0',
        },
    )
    _ensure_columns(
        conn,
        'entry_annotations',
        {
            'is_sensitive_override': 'INTEGER',
            'sensitivity_reason_override': 'TEXT',
        },
    )


def _run_safe_migrations(conn: sqlite3.Connection) -> None:
    """Apply lightweight, idempotent migrations for existing SQLite databases."""
    _ensure_columns(
        conn,
        'app_sessions',
        {
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
        },
    )
    _ensure_columns(
        conn,
        'browser_history_entries',
        {
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
        },
    )
    _ensure_columns(
        conn,
        'clipboard_entries',
        {
            'is_sensitive': 'INTEGER NOT NULL DEFAULT 0',
            'sensitivity_reason': 'TEXT',
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
        },
    )
    _ensure_columns(
        conn,
        'ai_prompt_entries',
        {
            'dedupe_key': 'TEXT',
            'char_count': 'INTEGER NOT NULL DEFAULT 0',
            'is_sensitive': 'INTEGER NOT NULL DEFAULT 0',
            'sensitivity_reason': 'TEXT',
            'is_selected': 'INTEGER NOT NULL DEFAULT 1',
            'is_deleted': 'INTEGER NOT NULL DEFAULT 0',
            'client_event_id': 'TEXT',
            'source': "TEXT NOT NULL DEFAULT 'edge_extension'",
        },
    )
    _ensure_columns(
        conn,
        'daily_reports',
        {
            'report_type': "TEXT NOT NULL DEFAULT 'daily'",
            'template_name': "TEXT NOT NULL DEFAULT 'daily_standard'",
            'model_provider': "TEXT NOT NULL DEFAULT 'deepseek'",
            'material_snapshot_json': 'TEXT',
            'material_summary': 'TEXT',
            'source_counts_json': "TEXT NOT NULL DEFAULT '{}'",
            'updated_at': "TEXT NOT NULL DEFAULT ''",
        },
    )
    _ensure_columns(
        conn,
        'app_profiles',
        {
            'icon_path': 'TEXT',
        },
    )
    _ensure_columns(
        conn,
        'entry_annotations',
        {
            'is_sensitive_override': 'INTEGER',
            'sensitivity_reason_override': 'TEXT',
        },
    )

    # Backfill updated_at for older daily_reports rows added before this field existed.
    if _table_exists(conn, 'daily_reports') and _column_exists(conn, 'daily_reports', 'updated_at'):
        conn.execute(
            """
            UPDATE daily_reports
            SET updated_at = COALESCE(NULLIF(updated_at, ''), created_at, datetime('now', 'localtime'))
            WHERE updated_at IS NULL OR updated_at = ''
            """
        )

    _ensure_indexes(conn)


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    try:
        conn.execute('DROP INDEX IF EXISTS idx_ai_prompt_entries_unique_prompt')
    except sqlite3.Error:
        logger.debug('Failed to drop obsolete ai prompt prompt_hash unique index.', exc_info=True)

    statements = [
        """
        CREATE INDEX IF NOT EXISTS idx_app_sessions_selected
        ON app_sessions(date, is_selected, is_deleted)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_app_categories_visible
        ON app_categories(is_deleted, sort_order, name)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_app_profiles_category
        ON app_profiles(category)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_app_profiles_process_name
        ON app_profiles(process_name)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_date
        ON ai_prompt_entries(date)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_timestamp
        ON ai_prompt_entries(timestamp)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_selected
        ON ai_prompt_entries(date, is_selected, is_deleted)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_daily_reports_date
        ON daily_reports(date)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_daily_reports_created_at
        ON daily_reports(created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_entry_annotations_source
        ON entry_annotations(source_type, source_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_entry_annotations_sensitive
        ON entry_annotations(source_type, is_sensitive_override)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_app_sessions_date_start_time
        ON app_sessions(date, start_time)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_clipboard_entries_date_first_seen
        ON clipboard_entries(date, first_seen_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_browser_history_entries_date_visit_time
        ON browser_history_entries(date, visit_time)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_date_timestamp
        ON ai_prompt_entries(date, timestamp)
        """,
    ]
    for sql in statements:
        try:
            conn.execute(sql)
        except sqlite3.Error:
            logger.debug('Failed to create migration index: %s', sql, exc_info=True)

    try:
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_prompt_entries_unique_dedupe
            ON ai_prompt_entries(date, platform, dedupe_key)
            WHERE dedupe_key IS NOT NULL AND dedupe_key <> ''
            """
        )
    except sqlite3.IntegrityError:
        logger.warning(
            'Skipped unique ai_prompt_entries(date, platform, dedupe_key) index because '
            'existing duplicate rows are present.'
        )
    except sqlite3.Error:
        logger.debug('Failed to create ai prompt unique index.', exc_info=True)


def _ensure_columns(
    conn: sqlite3.Connection,
    table_name: str,
    columns: dict[str, str],
) -> None:
    if not _table_exists(conn, table_name):
        return

    existing = _table_columns(conn, table_name)
    for column_name, ddl in columns.items():
        if column_name in existing:
            continue
        conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}')


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
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


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row['name']) for row in conn.execute(f'PRAGMA table_info({table_name})')}


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    return column_name in _table_columns(conn, table_name)


class SqliteConnectionFactory:
    """
    为每个长期运行的模块创建独立 SQLite connection

    注意:
    - factory 本身可以共享
    - factory.open() 每调用一次都会返回新的 connection
    - 不要把同一个 connection 在多个 collector 之间共享
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()

    def open(self) -> sqlite3.Connection:
        return create_connection(self.db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = self.open()
        try:
            yield conn
        finally:
            conn.close()
