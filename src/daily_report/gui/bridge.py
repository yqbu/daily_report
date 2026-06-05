from __future__ import annotations

import json
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.services.gui_service import GuiService

logger = logging.getLogger(__name__)


class ReportWorker(QObject):
    finished = Signal(str)

    def __init__(self, db_path: Path, options: dict[str, Any], job_id: str):
        super().__init__()
        self.db_path = db_path
        self.options = options
        self.job_id = job_id

    @Slot()
    def run(self) -> None:
        try:
            service = GuiService(GuiDataProvider(self.db_path))
            data = service.generate_report(self.options)
            self.finished.emit(_json_ok({"job_id": self.job_id, "result": data}))
        except Exception as exc:
            logger.exception('Report worker failed.')
            self.finished.emit(_json_error(str(exc), job_id=self.job_id))


class ModelTestWorker(QObject):
    finished = Signal(str)

    def __init__(self, params: dict[str, Any], job_id: str):
        super().__init__()
        self.params = params
        self.job_id = job_id

    @Slot()
    def run(self) -> None:
        try:
            data = GuiService().test_model_connection(self.params)
            self.finished.emit(_json_ok({"job_id": self.job_id, "result": data}))
        except Exception as exc:
            logger.exception('Model test worker failed.')
            self.finished.emit(_json_error(str(exc), job_id=self.job_id))


class PythonBridge(QObject):
    jobFinished = Signal(str)

    def __init__(self, service: GuiService | None = None):
        super().__init__()
        self.service = service or GuiService()
        self._jobs: dict[str, tuple[QThread, ReportWorker | ModelTestWorker]] = {}

    @Slot(str, result=str)
    def ping(self, payload: str = "") -> str:
        return _json_ok({"message": "pong", "payload": _payload(payload)})

    @Slot(str, result=str)
    def getOverview(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, lambda data: self.service.get_overview(_date_arg(data)))

    @Slot(str, result=str)
    def getTimeline(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.get_timeline)

    @Slot(str, result=str)
    def listEntries(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.list_entries(
                source_type=str(data.get("sourceType") or data.get("source_type") or ""),
                target_date=str(data.get("date") or "").strip() or None,
                start_date=str(data.get("startDate") or data.get("start_date") or "").strip() or None,
                end_date=str(data.get("endDate") or data.get("end_date") or "").strip() or None,
                filters=data.get("filters") if isinstance(data.get("filters"), dict) else {},
                page=int(data.get("page") or 1),
                page_size=int(data.get("pageSize") or data.get("page_size") or 30),
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def getEntryDetail(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> Any:
            raw_ids = data.get("ids")
            source_ids = [int(item) for item in raw_ids] if isinstance(raw_ids, list) else None
            return self.service.get_entry_detail(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
                source_ids,
                str(data.get("entryKey") or data.get("entry_key") or "").strip() or None,
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def updateEntrySelection(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            raw_ids = data.get("ids") or data.get("sourceIds") or data.get("source_ids")
            source_ids = [int(item) for item in raw_ids] if isinstance(raw_ids, list) else None
            return self.service.update_entry_selection(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
                bool(data.get("selected")),
                source_ids,
                str(data.get("entryKey") or data.get("entry_key") or "").strip() or None,
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def markEntryDeleted(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.mark_entry_deleted(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
                str(data.get("entryKey") or data.get("entry_key") or "").strip() or None,
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def updateEntryAnnotation(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            annotation_payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
            return self.service.update_entry_annotation(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
                annotation_payload,
                str(data.get("entryKey") or data.get("entry_key") or "").strip() or None,
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def updateEntrySensitive(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            raw_ids = data.get("ids")
            source_ids = [int(item) for item in raw_ids] if isinstance(raw_ids, list) else None
            return self.service.update_entry_sensitive(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
                bool(data.get("sensitive")),
                str(data.get("reason") or "").strip() or None,
                source_ids,
                str(data.get("entryKey") or data.get("entry_key") or "").strip() or None,
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def getDataCenterSummary(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.get_data_center_summary)

    @Slot(str, result=str)
    def getDataCenterAnalytics(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.get_data_center_analytics)

    @Slot(str, result=str)
    def get_data_center_summary(self, payload: str = "") -> str:
        return self.getDataCenterSummary(payload)

    @Slot(str, result=str)
    def get_data_center_analytics(self, payload: str = "") -> str:
        return self.getDataCenterAnalytics(payload)

    @Slot(str, result=str)
    def listAppProfiles(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.list_app_profiles)

    @Slot(str, result=str)
    def extractAppProfiles(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.extract_app_profiles)

    @Slot(str, result=str)
    def saveAppProfile(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.save_app_profile)

    @Slot(str, result=str)
    def resetAppProfile(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.reset_app_profile)

    @Slot(str, result=str)
    def deleteAppRecords(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.delete_app_records)

    @Slot(str, result=str)
    def listAppCategories(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.list_app_categories)

    @Slot(str, result=str)
    def saveAppCategory(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.save_app_category)

    @Slot(str, result=str)
    def deleteAppCategory(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.delete_app_category)

    @Slot(str, result=str)
    def getReportMaterials(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.get_report_materials)

    @Slot(str, result=str)
    def batchUpdateEntrySelection(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.batch_update_entry_selection)

    @Slot(str, result=str)
    def buildPrompt(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.build_prompt)

    @Slot(str, result=str)
    def generateReport(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.generate_report_sync)

    @Slot(str, result=str)
    def saveReport(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.save_report)

    @Slot(str, result=str)
    def getLatestReport(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, lambda data: self.service.get_latest_report(_date_arg(data)))

    @Slot(str, result=str)
    def listReports(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.list_reports)

    @Slot(str, result=str)
    def getReportDetail(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.get_report_detail_by_id)

    @Slot(str, result=str)
    def deleteReport(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.delete_report_by_id)

    @Slot(str, result=str)
    def getSettings(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, lambda _data: self.service.get_settings())

    @Slot(str, result=str)
    def saveSettings(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, self.service.save_settings)

    @Slot(str, result=str)
    def getHealth(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, lambda _data: self.service.get_health())

    @Slot(str, result=str)
    def get_dashboard_summary(self, payload: str = "") -> str:
        return self._call(payload, lambda data: self.service.get_dashboard_summary(_date_arg(data)))

    @Slot(str, result=str)
    def get_app_sessions(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_app_sessions)

    @Slot(str, result=str)
    def get_clipboard_entries(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_clipboard_entries)

    @Slot(str, result=str)
    def get_browser_entries(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_browser_entries)

    @Slot(str, result=str)
    def get_ai_prompt_entries(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_ai_prompt_entries)

    @Slot(str, result=str)
    def get_materials(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_materials)

    @Slot(str, result=str)
    def update_material_selected(self, payload: str = "") -> str:
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.update_material_selected(str(data.get("key") or ""), bool(data.get("selected")))

        return self._call(payload, run)

    @Slot(str, result=str)
    def get_report_history(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_report_history)

    @Slot(str, result=str)
    def get_report_detail(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_report_detail)

    @Slot(str, result=str)
    def generate_report(self, payload: str = "") -> str:
        try:
            options = _payload(payload)
            job_id = uuid.uuid4().hex
            worker = ReportWorker(self.service.provider.db_path, options, job_id)
            return self._start_worker(worker, job_id)
        except Exception as exc:
            logger.exception('Failed to start report worker.')
            return _json_error(str(exc))

    @Slot(str, result=str)
    def get_collector_status(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_collector_status)

    @Slot(str, result=str)
    def start_collector_service(self, payload: str = "") -> str:
        return self._call(payload, lambda _data: _run_collector_script("start"))

    @Slot(str, result=str)
    def stop_collector_service(self, payload: str = "") -> str:
        return self._call(payload, lambda _data: _run_collector_script("stop"))

    @Slot(str, result=str)
    def get_settings(self, payload: str = "") -> str:
        return self._call(payload, lambda _data: self.service.get_settings())

    @Slot(str, result=str)
    def save_settings(self, payload: str = "") -> str:
        return self._call(payload, self.service.save_settings)

    @Slot(str, result=str)
    def test_model_connection(self, payload: str = "") -> str:
        try:
            params = _payload(payload)
            job_id = uuid.uuid4().hex
            worker = ModelTestWorker(params, job_id)
            return self._start_worker(worker, job_id)
        except Exception as exc:
            logger.exception('Failed to start model test worker.')
            return _json_error(str(exc))

    @Slot(str, result=str)
    def build_report_prompt(self, payload: str = "") -> str:
        return self._call(payload, self.service.build_report_prompt)

    @Slot(str, result=str)
    def select_directory(self, payload: str = "") -> str:
        def run(data: dict[str, Any]) -> dict[str, Any]:
            title = str(data.get("title") or "选择目录")
            current_path = str(data.get("currentPath") or data.get("current_path") or "").strip()
            selected = QFileDialog.getExistingDirectory(None, title, current_path)
            return {"path": selected or ""}

        return self._call(payload, run)

    @Slot(str, result=str)
    def select_json_file(self, payload: str = "") -> str:
        def run(data: dict[str, Any]) -> dict[str, Any]:
            title = str(data.get("title") or "选择 JSON 文件")
            current_path = str(data.get("currentPath") or data.get("current_path") or "").strip()
            default_file_name = str(data.get("defaultFileName") or data.get("default_file_name") or "settings.json")
            initial_path = _dialog_initial_json_path(current_path, default_file_name)
            selected, _selected_filter = QFileDialog.getSaveFileName(
                None,
                title,
                str(initial_path),
                "JSON Files (*.json);;All Files (*)",
            )
            return {"path": selected or ""}

        return self._call(payload, run)

    def _call(self, payload: str, fn: Callable[[dict[str, Any]], Any]) -> str:
        try:
            return _json_ok(fn(_payload(payload)))
        except Exception as exc:
            logger.exception('Python bridge call failed.')
            return _json_error(str(exc))

    def _start_worker(self, worker: ReportWorker | ModelTestWorker, job_id: str) -> str:
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._emit_job_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda job_id=job_id: self._jobs.pop(job_id, None))
        self._jobs[job_id] = (thread, worker)
        thread.start()
        return _json_ok({"job_id": job_id, "status": "started"})

    @Slot(str)
    def _emit_job_finished(self, payload: str) -> None:
        self.jobFinished.emit(payload)


def _run_collector_script(action: str) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    script = _collector_script(repo_root, action)
    command = _script_command(script)
    kwargs = _subprocess_window_kwargs()

    process = subprocess.Popen(
        command,
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )
    return {"ok": True, "action": action, "pid": process.pid}


def _collector_script(repo_root: Path, action: str) -> Path:
    scripts_dir = repo_root / "scripts"
    candidates = [
        scripts_dir / f"{action}_collector.cmd",
        scripts_dir / f"{action}_collector.ps1",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Collector {action} script not found in {scripts_dir}")


def _script_command(script: Path) -> list[str]:
    suffix = script.suffix.lower()
    if os.name == "nt" and suffix in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(script)]
    if suffix == ".ps1":
        return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    return [str(script)]


def _dialog_initial_json_path(current_path: str, default_file_name: str) -> Path:
    if current_path:
        path = Path(current_path).expanduser()
        if path.suffix.lower() == ".json":
            return path
        return path / default_file_name
    return Path(default_file_name)


def _subprocess_window_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }


def _payload(payload: str) -> dict[str, Any]:
    if not payload:
        return {}
    data = json.loads(payload)
    return data if isinstance(data, dict) else {"value": data}


def _date_arg(data: dict[str, Any]) -> str | None:
    return str(data.get("date") or "").strip() or None


def _json_ok(data: Any) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False, default=str)


def _json_error(message: str, **extra: Any) -> str:
    payload: dict[str, Any] = {"ok": False, "error": message}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, default=str)
