from pathlib import Path
import time
import sqlite3

from daily_report.collector.foreground_collector import (
    ForegroundCollector,
    SqliteForegroundSessionStore,
)


def test_foreground_collector_write_db():
    db_path = Path(r"C:\Users\24331\AppData\Roaming\daily-report\daily_report.db")

    store = SqliteForegroundSessionStore(db_path)

    collector = ForegroundCollector(
        store=store,
        poll_interval_sec=1.0,
        idle_threshold_sec=180,
        split_on_title_change=True,
        flush_interval_sec=2.0,
    )

    # 第一次 poll：应该打开一个新 session，并 INSERT 一行
    collector.poll_once()

    # 等一会儿，让 duration 有数值
    time.sleep(2)

    # 第二次 poll：应该更新当前 session
    collector.poll_once()

    # 主动关闭当前 session，确保落库
    collector.stop()
    store.close()

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT id, app_name, process_name, window_title, duration_sec, active_duration_sec
        FROM app_sessions
        ORDER BY id DESC
        LIMIT 5
        """
    ).fetchall()
    conn.close()

    print(rows)

    assert len(rows) > 0