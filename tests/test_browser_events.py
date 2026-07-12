from __future__ import annotations

from fastapi.testclient import TestClient

from daily_report.api.app import create_app
from daily_report.api.deps import get_browser_event_service, get_overview_service, get_timeline_service
from daily_report.service.browser_event_service import BrowserEventService
from daily_report.service.material_service import MaterialService
from daily_report.service.overview_service import OverviewService
from daily_report.service.timeline_service import TimelineService
from daily_report.storage.database import create_connection, init_database
from daily_report.storage.repositories.browser_event_repository import BrowserEventRepository


def test_browser_event_repository_upserts_by_client_event_id(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    with create_connection(db_path) as conn:
        init_database(conn)
        repo = BrowserEventRepository(conn)
        first_id, first_duplicate = repo.upsert_event(
            {
                'date': '2026-06-04',
                'timestamp': '2026-06-04T10:00:00',
                'event_type': 'search',
                'url': 'https://www.google.com/search?q=fastapi',
                'title': 'fastapi - Google Search',
                'domain': 'www.google.com',
                'search_engine': 'google',
                'search_query': 'fastapi',
                'client_event_id': 'evt-1',
                'is_selected': True,
            }
        )
        second_id, second_duplicate = repo.upsert_event(
            {
                'date': '2026-06-04',
                'timestamp': '2026-06-04T10:00:01',
                'event_type': 'search',
                'url': 'https://www.google.com/search?q=fastapi',
                'search_query': 'fastapi',
                'client_event_id': 'evt-1',
                'is_selected': True,
            }
        )

    assert first_id == second_id
    assert first_duplicate is False
    assert second_duplicate is True


def test_browser_event_service_defaults_search_selected_and_sensitive_unselected(tmp_path):
    service = BrowserEventService(tmp_path / 'daily_report.db')

    normal = service.accept_event(
        {
            'event_type': 'search',
            'timestamp': '2026-06-04T10:00:00',
            'url': 'https://www.google.com/search?q=fastapi',
            'title': 'fastapi - Google Search',
            'search_engine': 'google',
            'search_query': 'fastapi',
            'client_event_id': 'normal-search',
        }
    )
    sensitive = service.accept_event(
        {
            'event_type': 'search',
            'timestamp': '2026-06-04T10:05:00',
            'url': 'https://www.google.com/search?q=api+key',
            'title': 'api key - Google Search',
            'search_query': 'api key secret',
            'client_event_id': 'sensitive-search',
        }
    )

    with create_connection(tmp_path / 'daily_report.db') as conn:
        normal_row = BrowserEventRepository(conn).get_by_id(normal['id'])
        sensitive_row = BrowserEventRepository(conn).get_by_id(sensitive['id'])

    assert normal_row is not None
    assert sensitive_row is not None
    assert bool(normal_row['is_selected']) is True
    assert bool(normal_row['is_sensitive']) is False
    assert bool(sensitive_row['is_selected']) is False
    assert bool(sensitive_row['is_sensitive']) is True


def test_browser_event_api_timeline_overview_and_materials(tmp_path):
    db_path = tmp_path / 'daily_report.db'
    app = create_app()
    app.dependency_overrides[get_browser_event_service] = lambda: BrowserEventService(db_path)
    app.dependency_overrides[get_timeline_service] = lambda: TimelineService(db_path)
    app.dependency_overrides[get_overview_service] = lambda: OverviewService(db_path)
    client = TestClient(app)

    health = client.get('/api/extension/health')
    assert health.status_code == 200
    assert health.json()['data']['browser_event_receiver'] == 'ok'

    posted = client.post(
        '/api/events/browser',
        json={
            'event_type': 'search',
            'timestamp': '2026-06-04T10:00:00',
            'url': 'https://www.bing.com/search?q=browser+events',
            'title': 'browser events - Bing',
            'search_engine': 'bing',
            'search_query': 'browser events',
            'client_event_id': 'api-browser-event',
        },
    )
    assert posted.status_code == 200
    assert posted.json()['data']['duplicated'] is False

    duplicate = client.post(
        '/api/events/browser',
        json={
            'event_type': 'search',
            'timestamp': '2026-06-04T10:00:00',
            'url': 'https://www.bing.com/search?q=browser+events',
            'search_query': 'browser events',
            'client_event_id': 'api-browser-event',
        },
    )
    assert duplicate.json()['data']['duplicated'] is True

    timeline = client.get('/api/timeline', params={'date': '2026-06-04', 'source_type': 'browser_event'})
    assert timeline.status_code == 200
    items = timeline.json()['data']['items']
    assert len(items) == 1
    assert items[0]['source_type'] == 'browser'
    assert items[0]['record_type'] == 'search'
    assert items[0]['entry_key'].startswith('browser:event:')
    assert items[0]['is_selected'] is True

    overview = client.get('/api/overview', params={'date': '2026-06-04'})
    assert overview.status_code == 200
    assert overview.json()['data']['browser_event_count'] == 1

    materials = MaterialService(db_path).build_materials('2026-06-04')
    assert any(material.source_type == 'browser' and material.record_type == 'search' for material in materials)
