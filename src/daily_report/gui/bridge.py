from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

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


class PythonBridge(QObject):
    jobFinished = Signal(str)

    def __init__(self, service: GuiService | None = None):
        super().__init__()
        self.service = service or GuiService()
        self._jobs: dict[str, tuple[QThread, ReportWorker]] = {}

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
                filters=data.get("filters") if isinstance(data.get("filters"), dict) else {},
                page=int(data.get("page") or 1),
                page_size=int(data.get("pageSize") or data.get("page_size") or 30),
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def getEntryDetail(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> Any:
            return self.service.get_entry_detail(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def updateEntrySelection(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.update_entry_selection(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
                bool(data.get("selected")),
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def markEntryDeleted(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.mark_entry_deleted(
                str(data.get("sourceType") or data.get("source_type") or ""),
                int(data.get("id") or 0),
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
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def getReportMaterials(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, lambda data: self.service.get_report_materials(_date_arg(data)))

    @Slot(str, result=str)
    def buildPrompt(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.build_prompt(
                _date_arg(data),
                str(data.get("templateName") or data.get("template_name") or "daily_standard"),
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def generateReport(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.generate_report_sync(
                _date_arg(data),
                str(data.get("templateName") or data.get("template_name") or "daily_standard"),
                str(data.get("apiKey") or data.get("api_key") or "").strip() or None,
            )

        return self._call(payload, run)

    @Slot(str, result=str)
    def getLatestReport(self, payload: str = "") -> str:  # noqa: N802
        return self._call(payload, lambda data: self.service.get_latest_report(_date_arg(data)))

    @Slot(str, result=str)
    def listReports(self, payload: str = "") -> str:  # noqa: N802
        def run(data: dict[str, Any]) -> dict[str, Any]:
            return self.service.list_reports(
                str(data.get("startDate") or data.get("start_date") or "").strip() or None,
                str(data.get("endDate") or data.get("end_date") or "").strip() or None,
            )

        return self._call(payload, run)

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
            thread = QThread(self)
            worker = ReportWorker(self.service.provider.db_path, options, job_id)
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
        except Exception as exc:
            logger.exception('Failed to start report worker.')
            return _json_error(str(exc))

    @Slot(str, result=str)
    def get_collector_status(self, payload: str = "") -> str:
        return self._call(payload, self.service.get_collector_status)

    @Slot(str, result=str)
    def get_settings(self, payload: str = "") -> str:
        return self._call(payload, lambda _data: self.service.get_settings())

    @Slot(str, result=str)
    def save_settings(self, payload: str = "") -> str:
        return self._call(payload, self.service.save_settings)

    @Slot(str, result=str)
    def test_model_connection(self, payload: str = "") -> str:
        return self._call(payload, self.service.test_model_connection)

    @Slot(str, result=str)
    def build_report_prompt(self, payload: str = "") -> str:
        return self._call(payload, self.service.build_report_prompt)

    def _call(self, payload: str, fn: Callable[[dict[str, Any]], Any]) -> str:
        try:
            return _json_ok(fn(_payload(payload)))
        except Exception as exc:
            logger.exception('Python bridge call failed.')
            return _json_error(str(exc))

    @Slot(str)
    def _emit_job_finished(self, payload: str) -> None:
        self.jobFinished.emit(payload)


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
