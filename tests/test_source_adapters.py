from __future__ import annotations

from datetime import datetime

import pytest

from daily_report.service.material_service import MaterialService
from daily_report.service.sensitivity import hash_text
from daily_report.service.timeline_service import TimelineService
from daily_report.sources.aliases import normalize_source_type
from daily_report.sources.registry import create_default_source_registry
from daily_report.storage.database import create_connection, init_database
from daily_report.storage.repositories.ai_prompt_repository import AiPromptEntryRepository
from daily_report.storage.repositories.app_session_repository import AppSessionRepository
from daily_report.storage.repositories.browser_history_repository import BrowserHistoryEntryRepository
from daily_report.storage.repositories.browser_event_repository import BrowserEventRepository
from daily_report.storage.repositories.clipboard_repository import ClipboardEntryRepository


def seed_four_sources(db_path, *, day: str = '2026-06-04') -> None:
    conn = create_connection(db_path)
    try:
        init_database(conn)
        now = datetime.fromisoformat(f'{day}T09:00:00')
        AppSessionRepository(conn).open_session(
            date=day,
            app_name='Code',
            process_name='code.exe',
            pid=1,
            hwnd=2,
            exe_path=None,
            window_title='SourceAdapter',
            start_time=now,
            end_time=now,
            duration_sec=120,
            active_duration_sec=120,
            is_active=True,
        )
        BrowserHistoryEntryRepository(conn).upsert_entry(
            date=day,
            browser='edge',
            profile_name='Default',
            visit_id=1,
            visit_time=now,
            visit_time_chrome=1,
            title='SourceAdapter search',
            url='https://www.bing.com/search?q=sourceadapter',
            domain='bing.com',
            transition=None,
            visit_duration_sec=0,
            is_search=True,
            search_engine='Bing',
            search_query='sourceadapter',
            is_noise=False,
            is_selected=True,
        )
        ClipboardEntryRepository(conn).upsert_entry(
            date=day,
            first_seen_at=now,
            last_seen_at=now,
            content='clipboard full text should stay private',
            content_preview='clipboard preview',
            content_hash=hash_text('clipboard full text should stay private'),
            char_count=39,
            is_sensitive=False,
            sensitivity_reason=None,
            is_selected=True,
        )
        AiPromptEntryRepository(conn).upsert_entry(
            date=day,
            timestamp=now,
            platform='ChatGPT',
            conversation_url='https://chatgpt.com/c/test',
            page_title='ChatGPT',
            prompt_text='full prompt text should not be material evidence',
            prompt_preview='prompt preview',
            prompt_hash=hash_text('full prompt text should not be material evidence'),
            dedupe_key='adapter-test',
            char_count=45,
            is_sensitive=False,
            sensitivity_reason=None,
            is_selected=True,
            client_event_id=None,
            source='edge_extension',
        )
        BrowserEventRepository(conn).insert_event(
            {
                'date': day,
                'timestamp': f'{day}T11:30:00',
                'event_type': 'search',
                'url': 'https://www.google.com/search?q=browser+event',
                'title': 'browser event - Google Search',
                'domain': 'www.google.com',
                'search_engine': 'google',
                'search_query': 'browser event',
                'client_event_id': 'browser-event-test',
                'source': 'edge_extension',
                'is_sensitive': False,
                'is_selected': True,
            }
        )
    finally:
        conn.close()


def test_source_registry_defaults_and_aliases(tmp_path):
    registry = create_default_source_registry(tmp_path / 'daily_report.db')

    assert registry.list_source_types() == ['app', 'browser', 'clipboard']
    assert registry.get('browser_history').source_type == 'browser'
    assert registry.get('ai').source_type == 'browser'
    assert registry.get('browser_event').source_type == 'browser'
    assert normalize_source_type('edge_history') == 'browser'
    with pytest.raises(ValueError):
        registry.get('bilibili')


def test_timeline_service_uses_source_adapters_and_aliases(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    seed_four_sources(db_path)

    timeline = TimelineService(db_path)
    events = timeline.list_timeline('2026-06-04')
    assert {event.source_type for event in events} == {'app', 'browser', 'clipboard'}
    assert {'search', 'ai_prompt'} <= {event.record_type for event in events if event.source_type == 'browser'}
    assert all(event.entry_key for event in events if event.source_type == 'browser')
    assert timeline.list_timeline('2026-06-04', source_types=['browser_history'])[0].source_type == 'browser'
    ai_events = timeline.list_timeline('2026-06-04', source_types=['ai'], record_type='ai_prompt')
    assert ai_events[0].source_type == 'browser'
    assert ai_events[0].record_type == 'ai_prompt'


def test_material_service_uses_preview_only_for_text_sources(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    seed_four_sources(db_path)

    materials = MaterialService(db_path).build_materials('2026-06-04')
    evidence = '\n'.join(material.evidence for material in materials)

    assert 'clipboard preview' in evidence
    assert 'clipboard full text should stay private' not in evidence
    assert 'prompt preview' in evidence
    assert 'full prompt text should not be material evidence' not in evidence
    assert 'browser+event' in evidence
