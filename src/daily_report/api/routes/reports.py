from __future__ import annotations

from dataclasses import asdict
from datetime import date as date_cls

from fastapi import APIRouter, Depends, Query

from daily_report.api.deps import get_report_service
from daily_report.api.response import ApiError, ok
from daily_report.api.schemas import BuildPromptRequest, GenerateReportRequest
from daily_report.service.report_service import ReportService

router = APIRouter(prefix='/api/reports', tags=['reports'])


@router.post('/build-prompt')
def build_prompt(
    payload: BuildPromptRequest,
    service: ReportService = Depends(get_report_service),
) -> dict:
    day = payload.date or date_cls.today().isoformat()
    try:
        prompt_text = service.build_prompt(day, template_name=payload.template_name)
    except Exception as exc:
        raise ApiError('Failed to build report prompt', 'PROMPT_BUILD_FAILED', 500) from exc
    return ok({'date': day, 'template_name': payload.template_name, 'prompt_text': prompt_text})


@router.post('/generate')
def generate_report(
    payload: GenerateReportRequest,
    service: ReportService = Depends(get_report_service),
) -> dict:
    day = payload.date or date_cls.today().isoformat()
    try:
        result = service.generate_report(
            day,
            template_name=payload.template_name,
            save=payload.save,
        )
    except ValueError as exc:
        if 'API key is missing' in str(exc):
            raise ApiError('API key is missing', 'MISSING_API_KEY', 400) from exc
        raise ApiError('Failed to generate report', 'REPORT_GENERATION_FAILED', 500) from exc
    except Exception as exc:
        raise ApiError('Failed to generate report', 'REPORT_GENERATION_FAILED', 500) from exc
    data = asdict(result)
    data['date'] = day
    data['template_name'] = payload.template_name
    return ok(data)


@router.get('/latest')
def get_latest_report(
    date: str | None = Query(default=None),
    service: ReportService = Depends(get_report_service),
) -> dict:
    day = date or date_cls.today().isoformat()
    try:
        record = service.get_latest_report(day)
    except Exception as exc:
        raise ApiError('Failed to query latest report', 'REPORT_QUERY_FAILED', 500) from exc
    return ok({'date': day, 'report': asdict(record) if record else None})
