from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from typing import Optional

from daily_report.config.paths import get_runtime_paths


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

    # 推荐开启 WAL，读写并发会更友好。
    conn.execute("PRAGMA journal_mode=WAL;")

    # 外键支持，后面如果加关联表会有用。
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")

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
