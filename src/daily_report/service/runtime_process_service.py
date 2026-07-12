from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from daily_report.config.local_settings import load_local_settings
from daily_report.config.paths import get_runtime_paths
from daily_report.storage.database import create_connection, default_db_path, init_database
from daily_report.storage.repositories.collector_state_repository import CollectorStateRepository
from daily_report.storage.repositories.runtime_process_repository import RuntimeProcessRepository

logger = logging.getLogger(__name__)

HEALTH_PORT = 8765
COLLECTOR_COMPONENTS = [
    'foreground',
    'clipboard',
    'edge_history',
    'ai_prompt',
    'ai_prompt_receiver',
    'browser_event_receiver',
    'cleanup_worker',
    'status_json_worker',
]


@dataclass
class RuntimeProcessInfo:
    pid: int
    parent_pid: int | None
    role: str
    process_name: str | None
    exe_path: str | None
    cmdline: list[str]
    cmdline_preview: str
    cwd: str | None
    username: str | None
    started_at: str | None
    cpu_percent: float | None
    memory_mb: float | None
    port: int | None
    status: str
    is_current_project: bool
    is_registered: bool
    is_orphan: bool
    is_duplicate: bool
    risk_level: str
    reason: str | None


@dataclass
class RuntimeComponentHealth:
    name: str
    display_name: str
    status: str
    enabled: bool
    last_success_at: str | None
    last_error_at: str | None
    last_error_message: str | None
    records_collected: int | None
    heartbeat_at: str | None


@dataclass
class RuntimeDiagnosticItem:
    code: str
    level: str
    title: str
    message: str
    fixable: bool
    action: str | None


@dataclass
class RuntimeSummary:
    api_status: str
    api_pid: int | None
    api_port: int | None
    collector_status: str
    collector_pid: int | None
    gui_status: str
    database_status: str
    yasb_status: str
    duplicate_process_count: int
    orphan_process_count: int
    warning_count: int
    error_count: int
    updated_at: str
    processes: list[RuntimeProcessInfo]
    components: list[RuntimeComponentHealth]
    diagnostics: list[RuntimeDiagnosticItem]


class RuntimeProcessService:
    """Observe and safely manage Daily Report runtime processes."""

    def __init__(self, db_path: str | Path | None = None, project_root: str | Path | None = None) -> None:
        paths = get_runtime_paths()
        self.project_root = Path(project_root or paths.project_root).resolve()
        self.db_path = Path(db_path or default_db_path()).resolve()
        self.data_dir = self.db_path.parent
        self.lock_path = self.data_dir / 'daily_report_collector.lock'
        self.status_json_path = paths.status_json_path
        self._ensure_database()

    def get_summary(self) -> RuntimeSummary:
        processes = self.list_processes()
        api = self.check_api_health(processes=processes)
        collector = self.check_collector_health(processes=processes)
        database = self.check_database_health(lightweight=True)
        yasb = self.check_yasb_status(processes=processes)
        components = self._list_component_health()
        diagnostics = self.run_doctor(processes=processes, include_database=False)
        duplicate_count = sum(1 for item in processes if item.is_duplicate)
        orphan_count = sum(1 for item in processes if item.is_orphan)
        return RuntimeSummary(
            api_status=str(api.get('status', 'unknown')),
            api_pid=int(api['pid']) if api.get('pid') else _first_pid_by_role(processes, 'api'),
            api_port=int(api['port']) if api.get('port') else None,
            collector_status=str(collector.get('status', 'unknown')),
            collector_pid=_first_pid_by_role(processes, 'collector'),
            gui_status=self._overall_role_status(processes, {'gui', 'tauri'}),
            database_status=str(database.get('status', 'unknown')),
            yasb_status=str(yasb.get('status', 'unknown')),
            duplicate_process_count=duplicate_count,
            orphan_process_count=orphan_count,
            warning_count=sum(1 for item in diagnostics if item.level == 'warning'),
            error_count=sum(1 for item in diagnostics if item.level == 'error'),
            updated_at=_now(),
            processes=processes,
            components=components,
            diagnostics=diagnostics,
        )

    def list_processes(self) -> list[RuntimeProcessInfo]:
        processes = self.detect_daily_report_processes()
        existing_pids = {item.pid for item in processes}
        try:
            with self._connect() as conn:
                RuntimeProcessRepository(conn).cleanup_stale_records(existing_pids)
        except Exception:
            logger.debug('Failed to cleanup stale runtime registry records.', exc_info=True)

        duplicate_roles = {'api', 'collector', 'gui', 'tauri', 'node'}
        role_keys: dict[str, set[str]] = {}
        for process in processes:
            if process.role in duplicate_roles:
                role_keys.setdefault(process.role, set()).add(_logical_process_key(process))
        primary_by_key = _primary_process_by_logical_key(processes)
        parent_pids = {process.pid for process in processes}
        updated: list[RuntimeProcessInfo] = []
        for process in processes:
            process_key = _logical_process_key(process)
            is_duplicate = len(role_keys.get(process.role, set())) > 1 and primary_by_key.get(process_key) == process.pid
            is_orphan = self._is_orphan(process, parent_pids)
            risk_level = 'safe'
            reason = process.reason
            if is_duplicate:
                risk_level = 'warning'
                reason = reason or f'multiple {process.role} processes detected'
            if is_orphan:
                risk_level = 'warning'
                reason = reason or 'parent process is gone'
            updated.append(
                RuntimeProcessInfo(
                    **{
                        **asdict(process),
                        'is_duplicate': is_duplicate,
                        'is_orphan': is_orphan,
                        'risk_level': risk_level,
                        'reason': reason,
                    }
                )
            )
        return sorted(updated, key=lambda item: (item.role, item.pid))

    def detect_daily_report_processes(self) -> list[RuntimeProcessInfo]:
        registered = self._registered_pids()
        ports_by_pid = self._ports_by_pid()
        items: list[RuntimeProcessInfo] = []
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'exe', 'cmdline', 'cwd', 'username', 'create_time', 'status']):
            try:
                info = proc.info
                pid = int(info.get('pid') or 0)
                cmdline = [str(part) for part in (info.get('cmdline') or [])]
                cwd = _string_or_none(info.get('cwd'))
                exe_path = _string_or_none(info.get('exe'))
                process_name = _string_or_none(info.get('name'))
                is_current, reason = self.is_current_project_process(
                    cmdline=cmdline,
                    cwd=cwd,
                    exe_path=exe_path,
                    pid=pid,
                    registered_pids=registered,
                )
                if not is_current:
                    continue
                role = self.identify_role(cmdline=cmdline, cwd=cwd, process_name=process_name)
                started_at = None
                if info.get('create_time'):
                    started_at = datetime.fromtimestamp(float(info['create_time'])).isoformat(timespec='seconds')
                memory_mb = None
                try:
                    memory_mb = round(proc.memory_info().rss / 1024 / 1024, 1)
                except (psutil.Error, OSError):
                    pass
                cpu_percent = None
                try:
                    cpu_percent = proc.cpu_percent(interval=None)
                except (psutil.Error, OSError):
                    pass
                items.append(
                    RuntimeProcessInfo(
                        pid=pid,
                        parent_pid=int(info['ppid']) if info.get('ppid') else None,
                        role=role,
                        process_name=process_name,
                        exe_path=exe_path,
                        cmdline=cmdline,
                        cmdline_preview=_preview_cmdline(cmdline),
                        cwd=cwd,
                        username=_string_or_none(info.get('username')),
                        started_at=started_at,
                        cpu_percent=cpu_percent,
                        memory_mb=memory_mb,
                        port=ports_by_pid.get(pid),
                        status=str(info.get('status') or 'unknown'),
                        is_current_project=True,
                        is_registered=pid in registered,
                        is_orphan=False,
                        is_duplicate=False,
                        risk_level='safe',
                        reason=reason,
                    )
                )
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except Exception:
                logger.debug('Failed to inspect process.', exc_info=True)
        return items

    def detect_orphan_processes(self) -> list[RuntimeProcessInfo]:
        return [item for item in self.list_processes() if item.is_orphan]

    def detect_duplicate_processes(self) -> list[RuntimeProcessInfo]:
        return [item for item in self.list_processes() if item.is_duplicate]

    def check_api_health(self, processes: list[RuntimeProcessInfo] | None = None) -> dict[str, Any]:
        api_processes = [item for item in (processes or self.list_processes()) if item.role == 'api']
        candidates = self._api_port_candidates(api_processes)
        if not candidates:
            candidates = [(HEALTH_PORT, self._port_owner_pid(HEALTH_PORT))]

        last_error = None
        occupied_candidate: tuple[int, int | None] | None = None
        for port, hinted_pid in candidates:
            owner_pid = self._port_owner_pid(port) or hinted_pid
            if owner_pid:
                occupied_candidate = (port, owner_pid)
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=1.5) as response:
                    payload = json.loads(response.read().decode('utf-8'))
                return {
                    'status': 'running' if payload.get('ok') else 'error',
                    'pid': owner_pid,
                    'port': port,
                    'port_owner_pid': owner_pid,
                    'error': None,
                }
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                last_error = str(exc)

        if occupied_candidate:
            port, owner_pid = occupied_candidate
            return {
                'status': 'warning',
                'pid': owner_pid,
                'port': port,
                'port_owner_pid': owner_pid,
                'error': f'port {port} is occupied but API health is unavailable',
            }

        return {
            'status': 'stopped',
            'pid': api_processes[0].pid if api_processes else None,
            'port': candidates[0][0] if candidates else HEALTH_PORT,
            'port_owner_pid': None,
            'error': last_error or 'API port is not listening',
        }

    def check_collector_health(self, processes: list[RuntimeProcessInfo] | None = None) -> dict[str, Any]:
        collector_processes = [item for item in (processes or self.list_processes()) if item.role == 'collector']
        states = self._collector_states()
        running_state = any(str(state.get('status')) == 'running' for state in states)
        stale_states = [state for state in states if str(state.get('status')) == 'running'] if running_state and not collector_processes else []
        if collector_processes:
            status = 'running'
        elif running_state:
            status = 'warning'
        else:
            status = 'stopped'
        return {
            'status': status,
            'pid': collector_processes[0].pid if collector_processes else None,
            'lock_path': str(self.lock_path),
            'states': states,
            'stale_state_count': len(stale_states),
            'message': 'collector_state says running, but no collector process was detected' if stale_states else None,
        }

    def get_collector_runtime_status(self) -> dict[str, Any]:
        return self.check_collector_health()

    def check_database_health(self, *, lightweight: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            'status': 'unknown',
            'db_path': str(self.db_path),
            'exists': self.db_path.exists(),
            'journal_mode': None,
            'busy_timeout': None,
            'db_size': self.db_path.stat().st_size if self.db_path.exists() else 0,
            'wal_size': _file_size(self.db_path.with_suffix(self.db_path.suffix + '-wal')),
            'last_error': None,
        }
        if not self.db_path.exists():
            result['status'] = 'error'
            result['last_error'] = 'database file does not exist'
            return result
        try:
            with self._connect() as conn:
                conn.execute('SELECT 1').fetchone()
                result['journal_mode'] = conn.execute('PRAGMA journal_mode').fetchone()[0]
                result['busy_timeout'] = conn.execute('PRAGMA busy_timeout').fetchone()[0]
                if not lightweight:
                    missing = [table for table in self._required_tables() if not self._table_exists(conn, table)]
                    if missing:
                        result['status'] = 'warning'
                        result['last_error'] = f'missing tables: {", ".join(missing)}'
                    else:
                        result['status'] = 'ok'
                        RuntimeProcessRepository(conn).update_heartbeat('doctor', os.getpid())
                else:
                    result['status'] = 'ok'
        except Exception as exc:
            logger.exception('Database health check failed.')
            result['status'] = 'error'
            result['last_error'] = str(exc)
        return result

    def check_yasb_status(self, processes: list[RuntimeProcessInfo] | None = None) -> dict[str, Any]:
        try:
            settings = load_local_settings()
            raw_path = str(settings.yasb.status_json_path or self.status_json_path).strip()
            path = Path(raw_path)
            if not path.exists():
                return {'status': 'not_configured', 'status_json_path': str(path), 'last_error': 'status JSON does not exist'}
            modified_at = datetime.fromtimestamp(path.stat().st_mtime)
            age_sec = (datetime.now() - modified_at).total_seconds()
            payload = json.loads(path.read_text(encoding='utf-8'))
            status = 'ok' if age_sec <= 180 else 'stale'
            return {
                'status': status,
                'status_json_path': str(path),
                'modified_at': modified_at.isoformat(timespec='seconds'),
                'age_sec': round(age_sec, 1),
                'tooltip_available': bool(payload.get('tooltip') or payload.get('text')),
                'collector_process_running': any(item.role == 'collector' for item in (processes or [])),
            }
        except Exception as exc:
            logger.debug('YASB status check failed.', exc_info=True)
            return {'status': 'error', 'status_json_path': str(self.status_json_path), 'last_error': str(exc)}

    def run_doctor(
        self,
        processes: list[RuntimeProcessInfo] | None = None,
        *,
        include_database: bool = True,
    ) -> list[RuntimeDiagnosticItem]:
        processes = processes or self.list_processes()
        items: list[RuntimeDiagnosticItem] = []
        api = self.check_api_health(processes=processes)
        collector = self.check_collector_health(processes=processes)
        yasb = self.check_yasb_status(processes=processes)
        if api['status'] != 'running':
            items.append(RuntimeDiagnosticItem('api_not_running', 'warning', 'API is not healthy', str(api.get('error') or 'API health endpoint is unavailable.'), False, None))
        if collector['status'] != 'running':
            items.append(RuntimeDiagnosticItem('collector_not_running', 'warning', 'Collector is not running', str(collector.get('message') or 'No active collector process was detected.'), True, 'start_collector'))
        if api.get('port_owner_pid') and api.get('status') != 'running':
            items.append(RuntimeDiagnosticItem('api_port_occupied', 'warning', 'API port is occupied', f'Port {api.get("port") or HEALTH_PORT} is owned by PID {api["port_owner_pid"]}.', False, None))
        duplicates = [item for item in processes if item.is_duplicate]
        if duplicates:
            items.append(RuntimeDiagnosticItem('duplicate_processes', 'warning', 'Duplicate processes detected', f'{len(duplicates)} Daily Report related processes look duplicated.', True, 'cleanup_orphans'))
        orphans = [item for item in processes if item.is_orphan]
        if orphans:
            items.append(RuntimeDiagnosticItem('orphan_processes', 'warning', 'Orphan processes detected', f'{len(orphans)} child processes can be safely reviewed.', True, 'cleanup_orphans'))
        stale_lock = self._stale_lock_diagnostic()
        if stale_lock:
            items.append(stale_lock)
        if include_database:
            db = self.check_database_health(lightweight=False)
            if db.get('status') == 'error':
                items.append(RuntimeDiagnosticItem('database_error', 'error', 'Database check failed', str(db.get('last_error') or 'SQLite is unavailable.'), False, None))
            elif db.get('status') == 'warning':
                items.append(RuntimeDiagnosticItem('database_warning', 'warning', 'Database has warnings', str(db.get('last_error') or 'SQLite check has warnings.'), True, 'repair'))
        if yasb.get('status') in {'stale', 'error'}:
            items.append(RuntimeDiagnosticItem('yasb_status_stale', 'warning', 'YASB status is stale', str(yasb.get('last_error') or 'status.json has not been updated recently.'), True, 'repair'))
        if not items:
            items.append(RuntimeDiagnosticItem('runtime_ok', 'info', 'Runtime looks healthy', 'No runtime warnings were detected.', False, None))
        return items

    def terminate_process(self, pid: int) -> dict[str, Any]:
        return self._stop_process(pid, force=False)

    def kill_process(self, pid: int) -> dict[str, Any]:
        return self._stop_process(pid, force=True)

    def cleanup_orphans(self, dry_run: bool = True, *, force: bool = False) -> dict[str, Any]:
        orphans = self.detect_orphan_processes()
        if dry_run:
            return {'dry_run': True, 'force': force, 'processes': [asdict(item) for item in orphans], 'terminated': []}
        terminated = []
        errors = []
        for item in orphans:
            try:
                result = self._stop_process(item.pid, force=force)
                terminated.append(result)
            except Exception as exc:
                logger.exception('Failed to cleanup orphan pid=%s', item.pid)
                errors.append({'pid': item.pid, 'error': str(exc)})
        return {'dry_run': False, 'force': force, 'processes': [asdict(item) for item in orphans], 'terminated': terminated, 'errors': errors}

    def repair_runtime_state(self) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []
        processes = self.list_processes()
        existing_pids = {proc.pid for proc in processes}
        with self._connect() as conn:
            stale = RuntimeProcessRepository(conn).cleanup_stale_records(existing_pids)
            actions.append({'action': 'cleanup_stale_runtime_processes', 'count': stale})
            stale_collector_states = 0
            if not any(proc.role == 'collector' for proc in processes):
                collector_repo = CollectorStateRepository(conn)
                for state in collector_repo.list_states():
                    if str(state.get('status')) == 'running':
                        collector_repo.mark_stopped(str(state.get('collector_name')))
                        stale_collector_states += 1
            actions.append({'action': 'mark_stale_collector_states_stopped', 'count': stale_collector_states})
        lock_action = self._repair_stale_lock()
        if lock_action:
            actions.append(lock_action)
        return {'ok': True, 'actions': actions}

    def start_collector_if_not_running(self) -> dict[str, Any]:
        status = self.check_collector_health()
        if status.get('status') == 'running':
            return {'already_running': True, **status}
        self.repair_runtime_state()
        command = [sys.executable, '-m', 'daily_report.main', 'run']
        log_path = get_runtime_paths().log_dir / 'collector-runtime.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        src_path = str(self.project_root / 'src')
        existing_pythonpath = env.get('PYTHONPATH')
        env['PYTHONPATH'] = src_path if not existing_pythonpath else f'{src_path}{os.pathsep}{existing_pythonpath}'
        kwargs: dict[str, Any] = {
            'cwd': str(self.project_root),
            'stdin': subprocess.DEVNULL,
            'close_fds': True,
            'env': env,
        }
        if os.name == 'nt':
            kwargs['creationflags'] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW
                | getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0)
            )
        with log_path.open('ab') as log_file:
            process = subprocess.Popen(command, stdout=log_file, stderr=log_file, **kwargs)
        time.sleep(1.5)
        exit_code = process.poll()
        if exit_code is not None:
            return {
                'started': False,
                'status': 'error',
                'pid': process.pid,
                'exit_code': exit_code,
                'command': command,
                'log_path': str(log_path),
                'log_tail': _tail_text(log_path),
            }
        return {'started': True, 'status': 'running', 'pid': process.pid, 'command': command, 'log_path': str(log_path)}

    def stop_collector_gracefully(self) -> dict[str, Any]:
        collectors = [item for item in self.list_processes() if item.role == 'collector']
        if not collectors:
            return {'ok': True, 'message': 'collector is not running', 'stopped': []}
        stopped = [self.terminate_process(item.pid) for item in collectors]
        return {'ok': True, 'stopped': stopped}

    def restart_collector(self) -> dict[str, Any]:
        stopped = self.stop_collector_gracefully()
        time.sleep(1)
        started = self.start_collector_if_not_running()
        return {'stopped': stopped, 'started': started}

    def register_current_process(self, role: str, *, port: int | None = None, lock_path: str | None = None) -> None:
        proc = psutil.Process(os.getpid())
        with self._connect() as conn:
            RuntimeProcessRepository(conn).register_process(
                role=role,
                pid=os.getpid(),
                parent_pid=os.getppid(),
                process_name=proc.name(),
                exe_path=proc.exe(),
                cmdline=proc.cmdline(),
                cwd=os.getcwd(),
                port=port,
                db_path=str(self.db_path),
                lock_path=lock_path or str(self.lock_path),
                started_by='runtime_service',
                status='running',
                started_at=datetime.fromtimestamp(proc.create_time()).isoformat(timespec='seconds'),
            )

    def update_current_process_heartbeat(self, role: str, *, last_error: str | None = None) -> None:
        with self._connect() as conn:
            RuntimeProcessRepository(conn).update_heartbeat(role, os.getpid(), last_error=last_error)

    def mark_current_process_exited(self) -> None:
        with self._connect() as conn:
            RuntimeProcessRepository(conn).mark_exited(os.getpid())

    def is_current_project_process(
        self,
        *,
        cmdline: list[str],
        cwd: str | None,
        exe_path: str | None,
        pid: int | None = None,
        registered_pids: set[int] | None = None,
    ) -> tuple[bool, str | None]:
        joined = ' '.join(cmdline).replace('\\', '/').lower()
        cwd_value = str(cwd or '').replace('\\', '/').lower()
        if pid is not None and registered_pids and pid in registered_pids:
            return True, 'registered in runtime_processes'
        if 'src/daily_report' in joined or 'daily_report.main' in joined or _has_token(cmdline, {'daily-report', 'daily-report.exe'}):
            return True, 'cmdline points to daily_report source'
        if _token_name(str(exe_path or '')) == 'daily_report.exe':
            return True, 'exe is Daily Report desktop app'
        if cwd_value and self._is_path_inside_project(cwd_value) and _has_project_runtime_marker(cmdline=cmdline, cwd=cwd_value):
            return True, 'cwd is inside current project runtime'
        return False, None

    def identify_role(self, *, cmdline: list[str], cwd: str | None, process_name: str | None) -> str:
        joined = ' '.join(cmdline).lower().replace('\\', '/')
        cwd_value = str(cwd or '').lower().replace('\\', '/')
        name = str(process_name or '').lower()
        tokens = [_token_name(part) for part in cmdline]
        has_daily_module = 'daily_report.main' in tokens or 'daily_report.main' in joined
        has_daily_script = 'daily-report' in tokens or 'daily-report.exe' in tokens
        if (has_daily_module or has_daily_script) and ('runtime' in tokens or ' runtime ' in f' {joined} '):
            return 'runtime_cli'
        if 'uvicorn' in joined or 'fastapi' in joined or ((has_daily_module or has_daily_script) and ('api' in tokens or ' api ' in f' {joined} ')):
            return 'api'
        if ((has_daily_module or has_daily_script) and ('run' in tokens or ' run ' in f' {joined} ')) or 'collector' in tokens:
            return 'collector'
        if (has_daily_module or has_daily_script) and 'gui' in tokens:
            return 'gui'
        if 'tauri' in joined or 'src-tauri' in cwd_value or 'daily_report.exe' in name:
            return 'tauri'
        node_markers = {'vite', 'npm', 'npm.cmd', 'pnpm', 'pnpm.cmd', 'yarn', 'yarn.cmd'}
        has_node_marker = bool(node_markers.intersection(tokens)) or ' vite ' in f' {joined} '
        if has_node_marker and (
            'frontend' in cwd_value or cwd_value == str(self.project_root).lower().replace('\\', '/')
        ):
            return 'node'
        if 'yasb_status' in joined or 'yasb' in joined:
            return 'yasb_script'
        return 'unknown_daily_report'

    def _stop_process(self, pid: int, *, force: bool) -> dict[str, Any]:
        current = {item.pid: item for item in self.list_processes()}
        info = current.get(int(pid))
        if info is None or not info.is_current_project:
            raise RuntimeError(f'PID {pid} is not a current Daily Report project process')
        if info.role in {'unknown_daily_report', 'runtime_cli'}:
            raise RuntimeError(f'PID {pid} is observable but not safe to manage automatically')
        if int(pid) == os.getpid():
            raise RuntimeError('Refusing to stop the current API/runtime process')
        proc = psutil.Process(int(pid))
        action = 'kill' if force else 'terminate'
        if force:
            proc.kill()
        else:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            pass
        with self._connect() as conn:
            RuntimeProcessRepository(conn).mark_exited(int(pid))
        logger.warning('Runtime %s sent to pid=%s role=%s', action, pid, info.role)
        return {'pid': int(pid), 'role': info.role, 'action': action, 'cmdline_preview': info.cmdline_preview}

    def _registered_pids(self) -> set[int]:
        try:
            with self._connect() as conn:
                return {int(row['pid']) for row in RuntimeProcessRepository(conn).list_active()}
        except Exception:
            logger.debug('Failed to read runtime process registry.', exc_info=True)
            return set()

    def _ports_by_pid(self) -> dict[int, int]:
        ports: dict[int, int] = {}
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.pid and conn.laddr and conn.status == psutil.CONN_LISTEN:
                    port = int(conn.laddr.port)
                    ports.setdefault(int(conn.pid), port)
        except (psutil.AccessDenied, OSError):
            pass
        return ports

    def _api_port_candidates(self, api_processes: list[RuntimeProcessInfo]) -> list[tuple[int, int | None]]:
        candidates: list[tuple[int, int | None]] = []
        seen: set[int] = set()
        for process in api_processes:
            for port in (process.port, _cmdline_option_int(process.cmdline, '--port')):
                if port and port not in seen:
                    candidates.append((port, process.pid))
                    seen.add(port)
        if HEALTH_PORT not in seen:
            owner = self._port_owner_pid(HEALTH_PORT)
            if owner:
                candidates.append((HEALTH_PORT, owner))
        return candidates

    def _port_owner_pid(self, port: int) -> int | None:
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.pid and conn.laddr and int(conn.laddr.port) == port and conn.status == psutil.CONN_LISTEN:
                    return int(conn.pid)
        except (psutil.AccessDenied, OSError):
            return None
        return None

    def _collector_states(self) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                return CollectorStateRepository(conn).list_states()
        except Exception:
            logger.debug('Failed to read collector states.', exc_info=True)
            return []

    def _list_component_health(self) -> list[RuntimeComponentHealth]:
        by_name = {str(row.get('collector_name')): row for row in self._collector_states()}
        components: list[RuntimeComponentHealth] = []
        for name in COLLECTOR_COMPONENTS:
            row = by_name.get(name)
            components.append(
                RuntimeComponentHealth(
                    name=name,
                    display_name=name.replace('_', ' ').title(),
                    status=str(row.get('status') if row else 'unknown'),
                    enabled=bool(row.get('enabled', True)) if row else False,
                    last_success_at=_string_or_none(row.get('last_success_at')) if row else None,
                    last_error_at=_string_or_none(row.get('last_error_at')) if row else None,
                    last_error_message=_string_or_none(row.get('last_error_message')) if row else None,
                    records_collected=int(row['records_collected']) if row and row.get('records_collected') is not None else None,
                    heartbeat_at=_string_or_none(row.get('updated_at')) if row else None,
                )
            )
        return components

    def _is_orphan(self, process: RuntimeProcessInfo, project_pids: set[int]) -> bool:
        if process.role in {'api', 'collector', 'runtime_cli', 'unknown_daily_report'}:
            return False
        if process.role not in {'gui', 'tauri', 'node', 'yasb_script'}:
            return False
        if not process.parent_pid or process.parent_pid in project_pids:
            return False
        if psutil.pid_exists(process.parent_pid):
            return False
        return process.is_current_project

    def _overall_role_status(self, processes: list[RuntimeProcessInfo], roles: set[str]) -> str:
        return 'running' if any(item.role in roles for item in processes) else 'stopped'

    def _stale_lock_diagnostic(self) -> RuntimeDiagnosticItem | None:
        owner_pid = self._read_lock_owner_pid()
        if owner_pid is None:
            return None
        if not psutil.pid_exists(owner_pid):
            return RuntimeDiagnosticItem('stale_lock', 'warning', 'Collector lock is stale', f'Lock owner PID {owner_pid} no longer exists.', True, 'repair')
        return None

    def _repair_stale_lock(self) -> dict[str, Any] | None:
        owner_pid = self._read_lock_owner_pid()
        if owner_pid is None or psutil.pid_exists(owner_pid):
            return None
        try:
            self.lock_path.unlink(missing_ok=True)
            return {'action': 'remove_stale_lock', 'pid': owner_pid, 'lock_path': str(self.lock_path)}
        except OSError as exc:
            return {'action': 'remove_stale_lock_failed', 'pid': owner_pid, 'error': str(exc)}

    def _read_lock_owner_pid(self) -> int | None:
        if not self.lock_path.exists():
            return None
        try:
            for line in self.lock_path.read_text(encoding='utf-8', errors='ignore').splitlines():
                if line.startswith('pid='):
                    return int(line.split('=', 1)[1].strip())
        except (OSError, ValueError):
            return None
        return None

    def _required_tables(self) -> list[str]:
        return ['app_sessions', 'clipboard_entries', 'browser_history_entries', 'collector_state', 'runtime_processes']

    def _table_exists(self, conn, table: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
            (table,),
        ).fetchone() is not None

    def _is_path_inside_project(self, value: str) -> bool:
        try:
            path = Path(value).resolve()
            return path == self.project_root or self.project_root in path.parents
        except OSError:
            return False

    def _ensure_database(self) -> None:
        conn = create_connection(self.db_path)
        try:
            init_database(conn)
        finally:
            conn.close()

    @contextmanager
    def _connect(self):
        conn = create_connection(self.db_path)
        try:
            yield conn
        finally:
            conn.close()


def summary_to_dict(summary: RuntimeSummary) -> dict[str, Any]:
    return asdict(summary)


def process_to_dict(process: RuntimeProcessInfo) -> dict[str, Any]:
    return asdict(process)


def diagnostic_to_dict(item: RuntimeDiagnosticItem) -> dict[str, Any]:
    return asdict(item)


def _first_pid_by_role(processes: list[RuntimeProcessInfo], role: str) -> int | None:
    for process in processes:
        if process.role == role:
            return process.pid
    return None


def _preview_cmdline(cmdline: list[str]) -> str:
    text = ' '.join(cmdline)
    return text if len(text) <= 220 else f'{text[:217]}...'


def _logical_process_key(process: RuntimeProcessInfo) -> str:
    if process.role in {'api', 'collector'}:
        cmdline_port = _cmdline_option_int(process.cmdline, '--port')
        if cmdline_port:
            return f'{process.role}:port:{cmdline_port}'
        return f'{process.role}:cmd:{process.cmdline_preview}'
    return f'{process.role}:pid:{process.pid}'


def _primary_process_by_logical_key(processes: list[RuntimeProcessInfo]) -> dict[str, int]:
    grouped: dict[str, list[RuntimeProcessInfo]] = {}
    for process in processes:
        grouped.setdefault(_logical_process_key(process), []).append(process)
    primary: dict[str, int] = {}
    for key, items in grouped.items():
        winner = max(
            items,
            key=lambda item: (
                item.port is not None,
                item.is_registered,
                float(item.memory_mb or 0),
                item.pid,
            ),
        )
        primary[key] = winner.pid
    return primary


def _has_project_runtime_marker(*, cmdline: list[str], cwd: str) -> bool:
    joined = ' '.join(cmdline).replace('\\', '/').lower()
    tokens = {_token_name(part) for part in cmdline}
    node_markers = {'vite', 'npm', 'npm.cmd', 'pnpm', 'pnpm.cmd', 'yarn', 'yarn.cmd'}
    if node_markers.intersection(tokens) or ' vite ' in f' {joined} ':
        return True
    if 'tauri' in joined or 'src-tauri' in cwd:
        return True
    if 'daily_report.main' in joined or _has_token(cmdline, {'daily-report', 'daily-report.exe'}):
        return True
    return False


def _has_token(cmdline: list[str], values: set[str]) -> bool:
    return bool({_token_name(part) for part in cmdline}.intersection(values))


def _cmdline_option_int(cmdline: list[str], option: str) -> int | None:
    for index, part in enumerate(cmdline):
        if part == option and index + 1 < len(cmdline):
            try:
                return int(cmdline[index + 1])
            except ValueError:
                return None
        if part.startswith(f'{option}='):
            try:
                return int(part.split('=', 1)[1])
            except ValueError:
                return None
    return None


def _tail_text(path: Path, *, limit: int = 4000) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ''
    return data[-limit:].decode('utf-8', errors='replace')


def _token_name(value: str) -> str:
    text = str(value).strip().lower().replace('\\', '/')
    if not text:
        return ''
    return Path(text).name


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
