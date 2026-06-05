from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from daily_report.api.deps import get_browser_event_service
from daily_report.api.response import ApiError, ok
from daily_report.service.browser_event_service import (
    ACCEPTED_BROWSER_EVENT_TYPES,
    BrowserEventService,
    api_time,
)

public_router = APIRouter(prefix='/api', tags=['extension'])
protected_router = APIRouter(prefix='/api', tags=['browser-events'])


@public_router.get('/extension/health')
def extension_health() -> dict[str, Any]:
    return ok(
        {
            'service': 'daily_report',
            'browser_event_receiver': 'ok',
            'api_time': api_time(),
            'accepted_event_types': ACCEPTED_BROWSER_EVENT_TYPES,
        }
    )


@protected_router.post('/events/browser')
def accept_browser_event(
    payload: dict[str, Any] = Body(default_factory=dict),
    service: BrowserEventService = Depends(get_browser_event_service),
) -> dict[str, Any]:
    try:
        result = service.accept_event(payload)
    except ValueError as exc:
        raise ApiError(str(exc), 'BROWSER_EVENT_INVALID', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to accept browser event', 'BROWSER_EVENT_ACCEPT_FAILED', 500) from exc
    return ok(result)


@protected_router.post('/ai-prompt')
def accept_ai_prompt(
    payload: dict[str, Any] = Body(default_factory=dict),
    service: BrowserEventService = Depends(get_browser_event_service),
) -> dict[str, Any]:
    try:
        result = service.accept_ai_prompt(payload)
    except ValueError as exc:
        raise ApiError(str(exc), 'AI_PROMPT_INVALID', 400) from exc
    except Exception as exc:
        raise ApiError('Failed to accept AI prompt', 'AI_PROMPT_ACCEPT_FAILED', 500) from exc
    return ok(result)


@protected_router.post('/ai-prompts')
def accept_ai_prompt_plural(
    payload: dict[str, Any] = Body(default_factory=dict),
    service: BrowserEventService = Depends(get_browser_event_service),
) -> dict[str, Any]:
    return accept_ai_prompt(payload=payload, service=service)
