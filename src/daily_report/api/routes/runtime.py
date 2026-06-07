from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from daily_report.api.deps import get_runtime_process_service
from daily_report.api.response import ApiError, ok
from daily_report.service.runtime_process_service import RuntimeProcessService, diagnostic_to_dict, process_to_dict, summary_to_dict

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/runtime', tags=['runtime'])


class CleanupOrphansRequest(BaseModel):
    dry_run: bool = True
    force: bool = False


class RepairRuntimeRequest(BaseModel):
    allow_kill: bool = False


@router.get('/summary')
def get_runtime_summary(service: RuntimeProcessService = Depends(get_runtime_process_service)) -> dict[str, Any]:
    logger.info('Runtime summary requested.')
    return ok(summary_to_dict(service.get_summary()))


@router.get('/processes')
def get_runtime_processes(service: RuntimeProcessService = Depends(get_runtime_process_service)) -> dict[str, Any]:
    return ok([process_to_dict(item) for item in service.list_processes()])


@router.get('/health')
def get_runtime_health(service: RuntimeProcessService = Depends(get_runtime_process_service)) -> dict[str, Any]:
    summary = service.get_summary()
    return ok(
        {
            'api_status': summary.api_status,
            'collector_status': summary.collector_status,
            'database_status': summary.database_status,
            'yasb_status': summary.yasb_status,
            'warning_count': summary.warning_count,
            'error_count': summary.error_count,
            'updated_at': summary.updated_at,
        }
    )


@router.post('/doctor')
def run_runtime_doctor(service: RuntimeProcessService = Depends(get_runtime_process_service)) -> dict[str, Any]:
    diagnostics = service.run_doctor()
    logger.info('Runtime doctor finished: %s diagnostics.', len(diagnostics))
    return ok([diagnostic_to_dict(item) for item in diagnostics])


@router.post('/repair')
def repair_runtime(
    request: RepairRuntimeRequest,
    service: RuntimeProcessService = Depends(get_runtime_process_service),
) -> dict[str, Any]:
    result = service.repair_runtime_state()
    logger.info('Runtime repair finished: %s', result)
    return ok(result)


@router.post('/cleanup-orphans')
def cleanup_orphans(
    request: CleanupOrphansRequest,
    service: RuntimeProcessService = Depends(get_runtime_process_service),
) -> dict[str, Any]:
    result = service.cleanup_orphans(dry_run=request.dry_run, force=request.force)
    logger.warning('Runtime cleanup-orphans requested: dry_run=%s force=%s', request.dry_run, request.force)
    return ok(result)


@router.post('/processes/{pid}/terminate')
def terminate_runtime_process(
    pid: int,
    service: RuntimeProcessService = Depends(get_runtime_process_service),
) -> dict[str, Any]:
    try:
        return ok(service.terminate_process(pid))
    except RuntimeError as exc:
        raise ApiError(str(exc), 'RUNTIME_PROCESS_REJECTED', 400) from exc


@router.post('/processes/{pid}/kill')
def kill_runtime_process(
    pid: int,
    service: RuntimeProcessService = Depends(get_runtime_process_service),
) -> dict[str, Any]:
    try:
        return ok(service.kill_process(pid))
    except RuntimeError as exc:
        raise ApiError(str(exc), 'RUNTIME_PROCESS_REJECTED', 400) from exc


@router.post('/collector/start')
def start_collector(service: RuntimeProcessService = Depends(get_runtime_process_service)) -> dict[str, Any]:
    try:
        return ok(service.start_collector_if_not_running())
    except Exception as exc:
        logger.exception('Failed to start collector.')
        raise ApiError('Failed to start collector', 'COLLECTOR_START_FAILED', 500) from exc


@router.post('/collector/stop')
def stop_collector(service: RuntimeProcessService = Depends(get_runtime_process_service)) -> dict[str, Any]:
    try:
        return ok(service.stop_collector_gracefully())
    except RuntimeError as exc:
        raise ApiError(str(exc), 'COLLECTOR_STOP_REJECTED', 400) from exc


@router.post('/collector/restart')
def restart_collector(service: RuntimeProcessService = Depends(get_runtime_process_service)) -> dict[str, Any]:
    try:
        return ok(service.restart_collector())
    except RuntimeError as exc:
        raise ApiError(str(exc), 'COLLECTOR_RESTART_REJECTED', 400) from exc
