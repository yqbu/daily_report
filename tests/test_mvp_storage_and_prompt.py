from __future__ import annotations

import sqlite3
from datetime import date, datetime

from daily_report.service.app_profile_service import AppProfileService
from daily_report.service.data_provider import DataProvider
from daily_report.service.desktop_service import DesktopService
from daily_report.service.material_service import MaterialService
from daily_report.service.overview_service import OverviewService
from daily_report.service.report_service import ReportService
from daily_report.service.sensitivity import detect_sensitive_text, hash_text, make_preview
from daily_report.config.local_settings import (
    CollectorSettings,
    LocalSettings,
    PrivacySettings,
    YasbSettings,
    get_settings_path,
    load_local_settings,
    save_local_settings,
)
from daily_report.service.timeline_service import TimelineService
from daily_report.storage.database import create_connection, init_database
from daily_report.storage.repositories.ai_prompt_repository import AiPromptEntryRepository
from daily_report.storage.repositories.app_session_repository import AppSessionRepository
from daily_report.storage.repositories.browser_history_repository import BrowserHistoryEntryRepository
from daily_report.storage.repositories.clipboard_repository import ClipboardEntryRepository


def test_database_initializes_all_mvp_tables(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    conn = create_connection(db_path)
    try:
        init_database(conn)
        tables = {
            row['name']
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        conn.close()

    assert {
        'app_sessions',
        'clipboard_entries',
        'browser_history_entries',
        'ai_prompt_entries',
        'daily_reports',
        'collector_state',
        'entry_annotations',
        'app_categories',
        'app_profiles',
    }.issubset(tables)


def test_old_database_gets_safe_columns(tmp_path):
    db_path = tmp_path / 'old.db'
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE app_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                app_name TEXT NOT NULL,
                process_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_sec REAL NOT NULL DEFAULT 0,
                active_duration_sec REAL NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_selected INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    conn = create_connection(db_path)
    try:
        init_database(conn)
        columns = {row['name'] for row in conn.execute('PRAGMA table_info(app_sessions)')}
    finally:
        conn.close()

    assert 'is_deleted' in columns


def test_repositories_and_timeline_roundtrip(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    conn = create_connection(db_path)
    try:
        init_database(conn)
        now = datetime(2026, 5, 23, 9, 30, 0)
        app_id = AppSessionRepository(conn).open_session(
            date='2026-05-23',
            app_name='PyCharm',
            process_name='pycharm64.exe',
            pid=100,
            hwnd=200,
            exe_path=None,
            window_title='daily_report - timeline_service.py',
            start_time=now,
            end_time=now,
            duration_sec=60,
            active_duration_sec=60,
            is_active=True,
        )
        ClipboardEntryRepository(conn).upsert_entry(
            date='2026-05-23',
            first_seen_at=now,
            last_seen_at=now,
            content='Tauri sidecar API',
            content_preview='Tauri sidecar API',
            content_hash=hash_text('Tauri sidecar API'),
            char_count=18,
            is_sensitive=False,
            sensitivity_reason=None,
            is_selected=True,
        )
        BrowserHistoryEntryRepository(conn).upsert_entry(
            date='2026-05-23',
            browser='edge',
            profile_name='Default',
            visit_id=1,
            visit_time=now,
            visit_time_chrome=1,
            title='Vue Router',
            url='https://router.vuejs.org/',
            domain='router.vuejs.org',
            transition=None,
            visit_duration_sec=10,
            is_search=False,
            search_engine=None,
            search_query=None,
            is_noise=False,
            is_selected=True,
        )
        ai_id, duplicated = AiPromptEntryRepository(conn).upsert_entry(
            date='2026-05-23',
            timestamp=now,
            platform='ChatGPT',
            conversation_url='https://chatgpt.com/c/test',
            page_title='ChatGPT',
            prompt_text='如何整理日报素材？',
            prompt_preview='如何整理日报素材？',
            prompt_hash=hash_text('如何整理日报素材？'),
            dedupe_key='dedupe-1',
            char_count=9,
            is_sensitive=False,
            sensitivity_reason=None,
            is_selected=True,
            client_event_id=None,
            source='edge_extension',
        )
        assert not duplicated
        second_id, duplicated = AiPromptEntryRepository(conn).upsert_entry(
            date='2026-05-23',
            timestamp=now,
            platform='ChatGPT',
            conversation_url='https://chatgpt.com/c/test',
            page_title='ChatGPT',
            prompt_text='如何整理日报素材？',
            prompt_preview='如何整理日报素材？',
            prompt_hash=hash_text('如何整理日报素材？'),
            dedupe_key='dedupe-2',
            char_count=9,
            is_sensitive=False,
            sensitivity_reason=None,
            is_selected=True,
            client_event_id=None,
            source='edge_extension',
        )
        assert second_id == ai_id
        assert duplicated
    finally:
        conn.close()

    timeline_service = TimelineService(db_path)
    events = timeline_service.list_timeline('2026-05-23')
    assert {event.source_type for event in events} == {'app', 'clipboard', 'browser'}
    assert any(event.record_type == 'ai_prompt' and event.entry_key for event in events)

    timeline_service.update_entry_selection('app', app_id, False)
    assert not TimelineService(db_path).get_entry_detail('app', app_id)['is_selected']

    timeline_service.mark_entry_deleted('app', app_id)
    assert TimelineService(db_path).get_entry_detail('app', app_id)['is_deleted']


def test_prompt_excludes_sensitive_material(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    conn = create_connection(db_path)
    try:
        init_database(conn)
        now = datetime(2026, 5, 23, 10, 0, 0)
        ClipboardEntryRepository(conn).upsert_entry(
            date='2026-05-23',
            first_seen_at=now,
            last_seen_at=now,
            content='api_key=sk-sensitive-token-123456789012345',
            content_preview='api_key=sk-sensitive-token-123456789012345',
            content_hash=hash_text('api_key=sk-sensitive-token-123456789012345'),
            char_count=43,
            is_sensitive=True,
            sensitivity_reason='token',
            is_selected=True,
        )
        AppSessionRepository(conn).open_session(
            date='2026-05-23',
            app_name='PyCharm',
            process_name='pycharm64.exe',
            pid=100,
            hwnd=200,
            exe_path=None,
            window_title='实现 MaterialService',
            start_time=now,
            end_time=now,
            duration_sec=60,
            active_duration_sec=60,
            is_active=True,
        )
    finally:
        conn.close()

    prompt = ReportService(db_path).build_prompt('2026-05-23')
    assert 'MaterialService' in prompt
    assert 'sk-sensitive-token' not in prompt


def test_app_profiles_override_app_materials_and_overview(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    target_date = date.today().isoformat()
    conn = create_connection(db_path)
    try:
        init_database(conn)
        now = datetime(2026, 5, 23, 11, 0, 0)
        AppSessionRepository(conn).open_session(
            date=target_date,
            app_name='Raw Tool',
            process_name='tool.exe',
            pid=101,
            hwnd=201,
            exe_path='C:\\Tools\\tool.exe',
            window_title='Secret Project Window',
            start_time=now,
            end_time=now,
            duration_sec=120,
            active_duration_sec=120,
            is_active=True,
        )
    finally:
        conn.close()

    app_profiles = AppProfileService(db_path)
    listed = app_profiles.list_profiles({'pageSize': 20})
    assert listed['counts']['all'] == 1
    assert listed['items'][0]['app_key'] == 'tool.exe'
    saved_mode_preview = app_profiles.list_profiles({
        'mode': 'saved',
        'extractIfEmpty': True,
        'observedScope': 'all',
        'pageSize': 20,
    })
    assert saved_mode_preview['total'] == 1
    assert saved_mode_preview['items'][0]['app_key'] == 'tool.exe'
    assert saved_mode_preview['items'][0]['requires_save']
    assert not saved_mode_preview['items'][0]['is_configured']

    saved = app_profiles.save_profile(
        {
            'app_key': 'tool.exe',
            'process_name': 'tool.exe',
            'exe_path': 'C:\\Tools\\tool.exe',
            'display_name': 'Tool Suite',
            'category': 'AI 辅助',
            'color': '#123456',
            'track_enabled': True,
            'capture_title_enabled': False,
        }
    )
    assert saved['effective_display_name'] == 'Tool Suite'
    assert saved['effective_color'] == '#123456'

    materials = MaterialService(db_path).build_materials(target_date)
    app_material = next(material for material in materials if material.source_type == 'app')
    assert app_material.title == 'Tool Suite'
    assert app_material.category == 'AI 辅助'
    assert app_material.evidence == 'Tool Suite'

    timeline_event = TimelineService(db_path).list_timeline(target_date, source_types=['app'])[0]
    assert timeline_event.title == 'Tool Suite'
    assert timeline_event.subtitle == ''
    assert timeline_event.category == 'AI 辅助'

    overview = OverviewService(db_path).get_overview(target_date)
    assert overview['top_apps'][0]['name'] == 'Tool Suite'
    assert overview['top_apps'][0]['color'] == '#123456'

    conn = create_connection(db_path)
    try:
        init_database(conn)
        AppSessionRepository(conn).open_session(
            date=target_date,
            app_name='Plain App',
            process_name='plain.exe',
            pid=102,
            hwnd=202,
            exe_path='C:\\Tools\\plain.exe',
            window_title='Plain Window',
            start_time=datetime(2026, 5, 23, 12, 0, 0),
            end_time=datetime(2026, 5, 23, 12, 1, 0),
            duration_sec=60,
            active_duration_sec=60,
            is_active=True,
        )
    finally:
        conn.close()

    all_profiles = app_profiles.list_profiles({'pageSize': 20})
    saved_only_profiles = app_profiles.list_profiles({
        'mode': 'saved',
        'extractIfEmpty': True,
        'observedScope': 'all',
        'pageSize': 20,
    })
    extracted_profiles = app_profiles.extract_profiles({'pageSize': 20})
    classified_profiles = app_profiles.list_profiles({
        'filters': {'classification': 'classified'},
        'pageSize': 20,
    })
    unclassified_profiles = app_profiles.list_profiles({
        'filters': {'classification': 'unclassified'},
        'pageSize': 20,
    })
    assert all_profiles['counts']['all'] == 2
    assert all_profiles['counts']['classified'] == 1
    assert all_profiles['counts']['unclassified'] == 1
    assert [item['app_key'] for item in saved_only_profiles['items']] == ['tool.exe']
    assert {item['app_key'] for item in extracted_profiles['items']} == {'tool.exe', 'plain.exe'}
    assert not next(item for item in extracted_profiles['items'] if item['app_key'] == 'tool.exe')['requires_save']
    assert next(item for item in extracted_profiles['items'] if item['app_key'] == 'plain.exe')['requires_save']
    assert classified_profiles['total'] == 1
    assert classified_profiles['counts'] == all_profiles['counts']
    assert unclassified_profiles['total'] == 1
    assert unclassified_profiles['counts'] == all_profiles['counts']

    name_sorted_profiles = app_profiles.list_profiles({
        'filters': {'sort_by': 'name', 'sort_direction': 'asc'},
        'pageSize': 20,
    })
    duration_sorted_profiles = app_profiles.list_profiles({
        'filters': {'sort_by': 'duration', 'sort_direction': 'desc'},
        'pageSize': 20,
    })
    assert [item['effective_display_name'] for item in name_sorted_profiles['items']] == [
        'Plain App',
        'Tool Suite',
    ]
    assert duration_sorted_profiles['items'][0]['effective_display_name'] == 'Tool Suite'

    app_profiles.save_profile(
        {
            'app_key': 'plain.exe',
            'process_name': 'plain.exe',
            'display_name': 'Plain App',
            'track_enabled': False,
        }
    )
    excluded_overview = OverviewService(db_path).get_overview(target_date)
    assert excluded_overview['active_time_sec'] == 120
    assert excluded_overview['app_session_count'] == 1
    assert {app['name'] for app in excluded_overview['top_apps']} == {'Tool Suite'}

    excluded_materials = MaterialService(db_path).build_materials(target_date)
    assert [material.title for material in excluded_materials if material.source_type == 'app'] == ['Tool Suite']

    report_stats = ReportService(db_path)._build_day_stats(target_date)
    assert report_stats['active_time_sec'] == 120
    assert report_stats['total_time_sec'] == 120

    reset = app_profiles.reset_profile({'app_key': 'tool.exe'})
    assert not reset['is_configured']
    assert reset['effective_display_name'] == 'Raw Tool'

    deleted = app_profiles.delete_app_records({'app_key': 'tool.exe', 'date': target_date})
    assert deleted['deleted_count'] == 1
    remaining_events = TimelineService(db_path).list_timeline(target_date, source_types=['app'])
    assert len(remaining_events) == 1
    assert remaining_events[0].title == 'Plain App'


def test_manual_app_profile_can_be_created_before_collection(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    conn = create_connection(db_path)
    try:
        init_database(conn)
    finally:
        conn.close()

    app_profiles = AppProfileService(db_path)
    icon_data_url = (
        'data:image/png;base64,'
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
    )
    saved = app_profiles.save_profile(
        {
            'app_key': 'manual.exe',
            'process_name': 'manual.exe',
            'display_name': 'Manual App',
            'category': '系统配置',
            'color': None,
            'icon_data_url': icon_data_url,
            'icon_file_name': 'manual.png',
            'track_enabled': False,
            'capture_title_enabled': True,
        }
    )
    assert saved['effective_display_name'] == 'Manual App'
    assert saved['session_count'] == 0
    assert saved['icon_base64'] is None
    assert saved['icon_path'] == 'app_icons/manual.exe.png'
    assert saved['icon_url'].startswith('data:image/png;base64,')
    icon_path = db_path.parent / saved['icon_path']
    assert icon_path.exists()

    listed = app_profiles.list_profiles({
        'filters': {'keyword': 'manual', 'track_enabled': False},
        'pageSize': 20,
        'include_unobserved': True,
    })
    assert listed['total'] == 1
    assert listed['items'][0]['app_key'] == 'manual.exe'
    assert listed['items'][0]['effective_display_name'] == 'Manual App'
    assert listed['items'][0]['icon_path'] == 'app_icons/manual.exe.png'

    app_profiles.reset_profile({'app_key': 'manual.exe'})
    assert not icon_path.exists()


def test_data_center_summary_uses_full_filtered_range_not_timeline_page(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    conn = create_connection(db_path)
    try:
        init_database(conn)
        repo = BrowserHistoryEntryRepository(conn)
        for index in range(220):
            day = '2026-05-23' if index < 150 else '2026-05-24'
            visit_time = datetime.fromisoformat(f'{day}T10:{index % 60:02d}:00')
            repo.upsert_entry(
                date=day,
                browser='Edge',
                profile_name='Default',
                visit_id=index + 1,
                visit_time=visit_time,
                visit_time_chrome=100000 + index,
                title=f'Data page {index}',
                url=f'https://example.com/{index}',
                domain='example.com',
                transition=None,
                visit_duration_sec=1,
                is_search=False,
                search_engine=None,
                search_query=None,
                is_noise=False,
                is_selected=True,
            )
    finally:
        conn.close()

    service = DesktopService(DataProvider(db_path))
    payload = {
        'startDate': '2026-05-23',
        'endDate': '2026-05-24',
        'filters': {'sourceTypes': ['browser']},
        'limit': 40,
        'offset': 0,
    }

    timeline = service.get_timeline(payload)
    summary = service.get_data_center_summary(payload)

    assert len(timeline['items']) == 40
    assert timeline['total'] == 220
    assert summary['total'] == 220
    assert summary['browser'] == 220
    assert summary['days'] == [
        {'date': '2026-05-24', 'count': 70},
        {'date': '2026-05-23', 'count': 150},
    ]


def test_sensitivity_helpers():
    assert make_preview(' a\n\nb ', 10) == 'a b'
    assert detect_sensitive_text('password=abc123456')[0]
    assert detect_sensitive_text('eyJabcdefghij.abcdefghijk.abcdefghijk')[0]


def test_custom_local_settings_path_is_remembered(tmp_path, monkeypatch):
    monkeypatch.setenv('DAILY_REPORT_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.delenv('DAILY_REPORT_SETTINGS_PATH', raising=False)

    custom_path = tmp_path / 'config' / 'custom_settings.json'
    settings = LocalSettings(
        collector=CollectorSettings(foreground_poll_interval_sec=9),
        privacy=PrivacySettings(sensitive_keywords=['client-secret']),
    )

    save_local_settings(settings, custom_path)

    assert get_settings_path() == custom_path.resolve()
    loaded = load_local_settings()
    assert loaded.collector.foreground_poll_interval_sec == 9
    assert loaded.privacy.sensitive_keywords == ['client-secret']


def test_local_settings_env_path_overrides_pointer(tmp_path, monkeypatch):
    monkeypatch.setenv('DAILY_REPORT_DATA_DIR', str(tmp_path / 'data'))

    pointer_path = tmp_path / 'config' / 'pointer_settings.json'
    env_path = tmp_path / 'config' / 'env_settings.json'
    save_local_settings(
        LocalSettings(collector=CollectorSettings(foreground_poll_interval_sec=7)),
        pointer_path,
    )

    monkeypatch.setenv('DAILY_REPORT_SETTINGS_PATH', str(env_path))
    save_local_settings(
        LocalSettings(collector=CollectorSettings(foreground_poll_interval_sec=13)),
        env_path,
    )

    assert get_settings_path() == env_path.resolve()
    assert load_local_settings().collector.foreground_poll_interval_sec == 13


def test_service_writes_configured_yasb_status_json(tmp_path, monkeypatch):
    monkeypatch.setenv('DAILY_REPORT_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.delenv('DAILY_REPORT_SETTINGS_PATH', raising=False)

    status_path = tmp_path / 'yasb' / 'status.json'
    save_local_settings(LocalSettings(yasb=YasbSettings(status_json_path=str(status_path))))

    from daily_report.service.app import DailyReportService

    service = DailyReportService()
    service.setup_database()
    service.write_status_json()

    assert status_path.exists()
    assert '"collector_status"' in status_path.read_text(encoding='utf-8')
