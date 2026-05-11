from datetime import datetime

from daily_report.storage.database import create_connection, init_database, default_db_path
from daily_report.storage.repositories import AppSessionRepository


def main():
    conn = create_connection()
    init_database(conn)

    repo = AppSessionRepository(conn)

    session_id = repo.open_session(
        date=datetime.now().date().isoformat(),
        app_name="Visual Studio Code",
        process_name="Code.exe",
        pid=12345,
        exe_path=r"C:\Users\Test\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        window_title="foreground_collector.py - daily_reporter - Visual Studio Code",
        start_time=datetime.now(),
        end_time=datetime.now(),
        duration_sec=0,
        active_duration_sec=0,
        is_active=True,
    )

    repo.update_session(
        session_id=session_id,
        end_time=datetime.now(),
        duration_sec=10.0,
        active_duration_sec=8.0,
        is_active=True,
    )

    today = datetime.now().date().isoformat()
    rows = repo.get_today_top_apps(today)

    print(f"DB path: {default_db_path()}")
    for row in rows:
        print(dict(row))

    conn.close()


if __name__ == "__main__":
    main()