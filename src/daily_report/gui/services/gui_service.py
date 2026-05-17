from __future__ import annotations

from dataclasses import asdict
from datetime import date as date_cls
from datetime import timedelta
from typing import Any

from daily_report.config.local_settings import load_local_settings, mask_api_key
from daily_report.gui.data_provider import GuiDataProvider
from daily_report.service.report_service import ReportService


class GuiService:
    """Stable JSON-friendly facade for the Vue Web UI.

    The Web UI should depend on this class instead of reaching into storage
    modules or legacy QWidget pages directly.
    """

    def __init__(self, provider: GuiDataProvider | None = None):
        self.provider = provider or GuiDataProvider()
        self.report_service = ReportService(self.provider.db_path)

    def get_dashboard_summary(self, target_date: str | None = None) -> dict[str, Any]:
        day = target_date or self.provider.today()
        raw = self.provider.dashboard(day)
        sessions = raw.get("sessions", [])
        return {
            "date": day,
            "metrics": {
                "active_time": raw.get("active_time", "0m"),
                "total_time": raw.get("total_time", "0m"),
                "app_sessions": raw.get("app_session_count", 0),
                "clipboard": raw.get("clipboard_count", 0),
                "browser": raw.get("browser_count", 0),
                "ai_prompts": raw.get("ai_prompt_count", 0),
            },
            "top_apps": raw.get("top_apps", []),
            "time_distribution": self._build_time_distribution(sessions),
            "recent_activities": self._recent_activities(sessions),
            "weekly_trend": self._weekly_trend(),
        }

    def get_app_sessions(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        day = self._day(params)
        page, page_size, offset = self._pagination(params)
        app_name = self._optional_filter(params.get("app_name") or params.get("appName"))
        keyword = str(params.get("keyword") or "").strip()
        if keyword:
            items, total = self._search_app_sessions(day, keyword, app_name, page_size, offset)
        else:
            items = self.provider.list_app_sessions(day, app_name=app_name, limit=page_size, offset=offset)
            total = self.provider.count_app_sessions(day, app_name=app_name)
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "app_names": self.provider.list_app_names(day),
        }

    def get_clipboard_entries(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        day = self._day(params)
        page, page_size, offset = self._pagination(params)
        keyword = str(params.get("keyword") or "")
        hide_sensitive = bool(params.get("hide_sensitive", params.get("hideSensitive", False)))
        items = self.provider.list_clipboard_entries(
            day,
            keyword=keyword,
            hide_sensitive=hide_sensitive,
            limit=page_size,
            offset=offset,
        )
        total = self.provider.count_clipboard_entries(day, keyword=keyword, hide_sensitive=hide_sensitive)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_browser_entries(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        day = self._day(params)
        page, page_size, offset = self._pagination(params)
        keyword = str(params.get("keyword") or "")
        domain = self._optional_filter(params.get("domain"))
        mode = str(params.get("mode") or "全部")
        hide_noise = bool(params.get("hide_noise", params.get("hideNoise", True)))
        items = self.provider.list_browser_history_entries(
            day,
            keyword=keyword,
            domain=domain,
            mode=mode,
            hide_noise=hide_noise,
            limit=page_size,
            offset=offset,
        )
        total = self.provider.count_browser_history_entries(
            day,
            keyword=keyword,
            domain=domain,
            mode=mode,
            hide_noise=hide_noise,
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "domains": self.provider.list_browser_domains(day),
        }

    def get_ai_prompt_entries(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        day = self._day(params)
        page, page_size, offset = self._pagination(params)
        keyword = str(params.get("keyword") or "")
        platform = self._optional_filter(params.get("platform"))
        hide_sensitive = bool(params.get("hide_sensitive", params.get("hideSensitive", False)))
        items = self.provider.list_ai_prompt_entries(
            day,
            keyword=keyword,
            platform=platform,
            hide_sensitive=hide_sensitive,
            limit=page_size,
            offset=offset,
        )
        total = self.provider.count_ai_prompt_entries(
            day,
            keyword=keyword,
            platform=platform,
            hide_sensitive=hide_sensitive,
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "platforms": self.provider.list_ai_platforms(day),
        }

    def get_materials(self, target_date: str | dict[str, Any] | None = None) -> dict[str, Any]:
        if isinstance(target_date, dict):
            day = self._day(target_date)
        else:
            day = target_date or self.provider.today()
        rows = self.provider.list_materials(day)
        return {
            "items": [asdict(row) for row in rows],
            "total": len(rows),
            "selected": sum(1 for row in rows if row.selected),
        }

    def update_material_selected(self, key: str, selected: bool) -> dict[str, Any]:
        self.provider.update_material_selected(key, selected)
        return {"key": key, "selected": selected}

    def get_report_history(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        page, page_size, offset = self._pagination(params)
        day = str(params.get("date") or "").strip() or None
        keyword = str(params.get("keyword") or "")
        rows = self.provider.list_daily_reports(day=day, keyword=keyword, limit=page_size, offset=offset)
        total = self.provider.count_daily_reports(day=day, keyword=keyword)
        return {"items": rows, "total": total, "page": page, "page_size": page_size}

    def get_report_detail(self, report_id: int | str | dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(report_id, dict):
            report_id = report_id.get("report_id") or report_id.get("reportId") or report_id.get("id")
        if report_id in (None, ""):
            return None
        return self.provider.get_daily_report(int(report_id))

    def generate_report(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        result = self.report_service.generate_report(
            target_date=str(options.get("date") or "").strip() or None,
            api_key=str(options.get("api_key") or options.get("apiKey") or "").strip() or None,
            save=bool(options.get("save", True)),
        )
        return asdict(result)

    def get_collector_status(self, target_date: str | dict[str, Any] | None = None) -> dict[str, Any]:
        if isinstance(target_date, dict):
            day = str(target_date.get("date") or "").strip() or None
        else:
            day = target_date
        return self.provider.status(day)

    def get_settings(self) -> dict[str, Any]:
        settings = load_local_settings()
        data = asdict(settings)
        data["model"]["api_key"] = mask_api_key(data["model"].get("api_key", ""))
        return data

    def build_report_prompt(self, target_date: str | dict[str, Any] | None = None) -> dict[str, Any]:
        if isinstance(target_date, dict):
            day = str(target_date.get("date") or "").strip() or None
            max_chars = target_date.get("max_chars") or target_date.get("maxChars")
        else:
            day = target_date
            max_chars = None
        prompt = self.report_service.build_prompt(day, max_chars=int(max_chars) if max_chars else None)
        return {"prompt": prompt}

    @staticmethod
    def _day(params: dict[str, Any]) -> str:
        return str(params.get("date") or date_cls.today().isoformat())

    @staticmethod
    def _optional_filter(value: Any) -> str | None:
        text = str(value or "").strip()
        if not text or text.lower() == "all" or text == "全部":
            return None
        return text

    @staticmethod
    def _pagination(params: dict[str, Any]) -> tuple[int, int, int]:
        page = max(1, int(params.get("page") or 1))
        page_size = max(1, min(100, int(params.get("page_size") or params.get("pageSize") or 30)))
        return page, page_size, (page - 1) * page_size

    @staticmethod
    def _time(value: Any) -> str:
        text = str(value or "")
        return text[11:19] if len(text) >= 19 else text

    @classmethod
    def _recent_activities(cls, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = list(reversed(sessions[-8:]))
        return [
            {
                "time": cls._time(row.get("start_time")),
                "title": row.get("window_title") or row.get("app_name") or "",
                "source": row.get("app_name") or "",
                "duration_sec": row.get("active_duration_sec") or row.get("duration_sec") or 0,
            }
            for row in rows
        ]

    @staticmethod
    def _build_time_distribution(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        slots = [{"label": f"{hour:02d}:00", "active": 0} for hour in range(24)]
        for row in sessions:
            start = str(row.get("start_time") or "")
            try:
                hour = int(start[11:13])
            except (TypeError, ValueError):
                continue
            if 0 <= hour < 24:
                slots[hour]["active"] += int(row.get("active_duration_sec") or row.get("duration_sec") or 1)
        return slots

    def _weekly_trend(self) -> list[dict[str, Any]]:
        today = date_cls.today()
        points: list[dict[str, Any]] = []
        for index in range(6, -1, -1):
            day = today - timedelta(days=index)
            points.append({"date": day.isoformat(), "count": self.provider.count_app_sessions(day.isoformat())})
        return points

    def _search_app_sessions(
        self,
        day: str,
        keyword: str,
        app_name: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        sql = "FROM app_sessions WHERE date = ?"
        params: list[Any] = [day]
        if app_name:
            sql += " AND app_name = ?"
            params.append(app_name)
        sql += " AND (app_name LIKE ? OR process_name LIKE ? OR window_title LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like])
        conn = self.provider.connect()
        try:
            total_row = conn.execute(f"SELECT COUNT(*) AS n {sql}", tuple(params)).fetchone()
            rows = conn.execute(
                f"SELECT * {sql} ORDER BY start_time ASC LIMIT ? OFFSET ?",
                tuple([*params, limit, offset]),
            ).fetchall()
            return [dict(row) for row in rows], int(total_row["n"] if total_row else 0)
        finally:
            conn.close()
