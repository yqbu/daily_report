from __future__ import annotations

from typing import Optional

import os
import sqlite3
from pathlib import Path


def default_db_path() -> Path:
    """
    默认数据库路径:
    Windows 下默认放到 %APPDATA%/daily-report/daily_report.db
    """
    appdata = os.getenv("APPDATA")

    if appdata:
        return Path(appdata) / "daily-report" / "daily_report.db"

    return Path.home() / ".daily-report" / "daily_report.db"


def create_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """
    创建 SQLite 连接
    """
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # 推荐开启 WAL，读写并发会更友好。
    conn.execute("PRAGMA journal_mode=WAL;")

    # 外键支持，后面如果加关联表会有用。
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


def init_database(conn: sqlite3.Connection, schema_path: str | Path | None = None) -> None:
    """
    初始化数据库表结构
    """
    if schema_path is None:
        schema_path = Path(__file__).with_name("schema.sql")

    schema_sql = Path(schema_path).read_text(encoding="utf-8")

    conn.executescript(schema_sql)
    conn.commit()