CREATE TABLE IF NOT EXISTS app_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    date TEXT NOT NULL,

    app_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    pid INTEGER,
    hwnd INTEGER,
    exe_path TEXT,
    window_title TEXT,

    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,

    duration_sec REAL NOT NULL DEFAULT 0,
    active_duration_sec REAL NOT NULL DEFAULT 0,

    is_active INTEGER NOT NULL DEFAULT 1,
    is_selected INTEGER NOT NULL DEFAULT 1,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_sessions_date
ON app_sessions(date);

CREATE INDEX IF NOT EXISTS idx_app_sessions_start_time
ON app_sessions(start_time);

CREATE INDEX IF NOT EXISTS idx_app_sessions_process_name
ON app_sessions(process_name);