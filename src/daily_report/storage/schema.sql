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
    is_deleted INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_sessions_date
ON app_sessions(date);

CREATE INDEX IF NOT EXISTS idx_app_sessions_start_time
ON app_sessions(start_time);

CREATE INDEX IF NOT EXISTS idx_app_sessions_process_name
ON app_sessions(process_name);

CREATE INDEX IF NOT EXISTS idx_app_sessions_selected
ON app_sessions(date, is_selected, is_deleted);

CREATE TABLE IF NOT EXISTS app_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_categories_visible
ON app_categories(is_deleted, sort_order, name);

CREATE TABLE IF NOT EXISTS app_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    app_key TEXT NOT NULL UNIQUE,
    process_name TEXT NOT NULL,
    exe_path TEXT,

    display_name TEXT,
    category TEXT,
    color TEXT,
    icon_base64 TEXT,

    track_enabled INTEGER NOT NULL DEFAULT 1,
    capture_title_enabled INTEGER NOT NULL DEFAULT 1,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_profiles_category
ON app_profiles(category);

CREATE INDEX IF NOT EXISTS idx_app_profiles_process_name
ON app_profiles(process_name);

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

CREATE TABLE IF NOT EXISTS ai_prompt_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    date TEXT NOT NULL,
    timestamp TEXT NOT NULL,

    platform TEXT NOT NULL,
    conversation_url TEXT,
    page_title TEXT,

    prompt_text TEXT NOT NULL,
    prompt_preview TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    dedupe_key TEXT,
    char_count INTEGER NOT NULL DEFAULT 0,

    is_sensitive INTEGER NOT NULL DEFAULT 0,
    sensitivity_reason TEXT,
    is_selected INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER NOT NULL DEFAULT 0,

    client_event_id TEXT,
    source TEXT NOT NULL DEFAULT 'edge_extension',

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_prompt_entries_unique_dedupe
ON ai_prompt_entries(date, platform, dedupe_key)
WHERE dedupe_key IS NOT NULL AND dedupe_key <> '';

CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_date
ON ai_prompt_entries(date);

CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_timestamp
ON ai_prompt_entries(timestamp);

CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_platform
ON ai_prompt_entries(platform);

CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_selected
ON ai_prompt_entries(date, is_selected, is_deleted);

CREATE INDEX IF NOT EXISTS idx_ai_prompt_entries_sensitive
ON ai_prompt_entries(date, is_sensitive, is_deleted);

CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    report_type TEXT NOT NULL DEFAULT 'daily',
    template_name TEXT NOT NULL DEFAULT 'daily_standard',
    model_provider TEXT NOT NULL DEFAULT 'deepseek',
    model_name TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    report_markdown TEXT NOT NULL,
    material_snapshot_json TEXT,
    material_summary TEXT,
    source_counts_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_date
ON daily_reports(date);

CREATE INDEX IF NOT EXISTS idx_daily_reports_created_at
ON daily_reports(created_at);

CREATE TABLE IF NOT EXISTS collector_state (
    collector_name TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'unknown',
    last_success_at TEXT,
    last_error_at TEXT,
    last_error_message TEXT,
    records_collected INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK(source_type IN ('app', 'browser', 'clipboard', 'ai_prompt')),
    source_id INTEGER NOT NULL,
    category TEXT,
    note TEXT,
    importance INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_type, source_id)
);

CREATE INDEX IF NOT EXISTS idx_entry_annotations_source
ON entry_annotations(source_type, source_id);
