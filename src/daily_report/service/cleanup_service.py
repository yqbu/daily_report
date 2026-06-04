from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_database(
    conn: sqlite3.Connection,
    *,
    retention_days: int = 7,
    report_retention_days: int | None = 90,
    vacuum: bool = False,
) -> None:
    """
    清理超过保留期的历史数据

    retention_days:
        普通采集数据保留天数, 例如 app_sessions / clipboard / browser / ai prompts

    report_retention_days:
        日报保留天数: None 表示不删除日报

    vacuum:
        是否执行 VACUUM; DELETE 只会释放 SQLite 内部页, 不一定立刻缩小 db 文件
        VACUUM 会真正压缩数据库文件, 但会更重, 不建议每次启动都执行
    """
    cutoff_date = (date.today() - timedelta(days=retention_days)).isoformat()

    logger.info('Cleanup database records older than %s', cutoff_date)

    table_date_columns = [
        ('app_sessions', 'date'),
        ('clipboard_entries', 'date'),
        ('browser_history_entries', 'date'),
        ('ai_prompt_entries', 'date'),
        ('browser_events', 'date'),
    ]

    for table, date_col in table_date_columns:
        if _table_exists(conn, table):
            deleted = _delete_older_than(conn, table, date_col, cutoff_date)
            logger.info('Cleanup table=%s, deleted=%s', table, deleted)

    if report_retention_days is not None and _table_exists(conn, 'daily_reports'):
        report_cutoff = (
            datetime.now() - timedelta(days=report_retention_days)
        ).isoformat(timespec='seconds')

        deleted = _delete_older_than(
            conn,
            'daily_reports',
            'created_at',
            report_cutoff,
        )
        logger.info('Cleanup table=daily_reports, deleted=%s', deleted)

    conn.commit()

    if vacuum:
        logger.info('Run SQLite VACUUM')
        conn.execute('VACUUM')


def cleanup_logs(
    log_dir: str | Path,
    *,
    retention_days: int = 7,
    patterns: tuple[str, ...] = ('*.log', '*.txt'),
) -> None:
    """
    删除超过 retention_days 的日志文件
    """
    log_dir = Path(log_dir)

    if not log_dir.exists():
        return

    cutoff_time = datetime.now() - timedelta(days=retention_days)

    for pattern in patterns:
        for path in log_dir.glob(pattern):
            if not path.is_file():
                continue

            modified_time = datetime.fromtimestamp(path.stat().st_mtime)

            if modified_time < cutoff_time:
                try:
                    path.unlink()
                    logger.info('Deleted old log file: %s', path)
                except OSError:
                    logger.exception('Failed to delete old log file: %s', path)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table,),
    ).fetchone()

    return row is not None


def _delete_older_than(
    conn: sqlite3.Connection,
    table: str,
    date_col: str,
    cutoff: str,
) -> int:
    cursor = conn.execute(
        f"""
        DELETE FROM {table}
        WHERE {date_col} < ?
        """,
        (cutoff,),
    )

    return int(cursor.rowcount or 0)
