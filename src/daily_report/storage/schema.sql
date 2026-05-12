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

CREATE TABLE IF NOT EXISTS clipboard_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    date TEXT NOT NULL,

    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,

    content TEXT NOT NULL,
    content_preview TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    char_count INTEGER NOT NULL DEFAULT 0,

    is_sensitive INTEGER NOT NULL DEFAULT 0,
    sensitivity_reason TEXT,

    is_selected INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,

    seen_count INTEGER NOT NULL DEFAULT 1,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE(date, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_clipboard_entries_date
ON clipboard_entries(date);

CREATE INDEX IF NOT EXISTS idx_clipboard_entries_last_seen_at
ON clipboard_entries(last_seen_at);

CREATE INDEX IF NOT EXISTS idx_clipboard_entries_hash
ON clipboard_entries(content_hash);

CREATE INDEX IF NOT EXISTS idx_clipboard_entries_selected
ON clipboard_entries(date, is_selected, is_deleted);

CREATE TABLE IF NOT EXISTS browser_history_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    date TEXT NOT NULL,

    browser TEXT NOT NULL,
    profile_name TEXT NOT NULL,

    visit_id INTEGER NOT NULL,
    visit_time TEXT NOT NULL,
    visit_time_chrome INTEGER NOT NULL,

    title TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    domain TEXT,

    transition INTEGER,
    visit_duration_sec REAL NOT NULL DEFAULT 0,

    is_search INTEGER NOT NULL DEFAULT 0,
    search_engine TEXT,
    search_query TEXT,

    is_noise INTEGER NOT NULL DEFAULT 0,
    is_selected INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE(browser, profile_name, visit_id)
);

CREATE INDEX IF NOT EXISTS idx_browser_history_entries_date
ON browser_history_entries(date);

CREATE INDEX IF NOT EXISTS idx_browser_history_entries_visit_time
ON browser_history_entries(visit_time);

CREATE INDEX IF NOT EXISTS idx_browser_history_entries_domain
ON browser_history_entries(domain);

CREATE INDEX IF NOT EXISTS idx_browser_history_entries_search
ON browser_history_entries(date, is_search, is_deleted);

CREATE INDEX IF NOT EXISTS idx_browser_history_entries_selected
ON browser_history_entries(date, is_selected, is_deleted);

CREATE INDEX IF NOT EXISTS idx_browser_history_entries_visit_time_chrome
ON browser_history_entries(browser, profile_name, visit_time_chrome);