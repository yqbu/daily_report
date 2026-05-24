from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from datetime import date as date_cls
from datetime import timedelta
from typing import Any

from daily_report.config.local_settings import (
    CollectorSettings,
    LocalSettings,
    LoggingSettings,
    ModelSettings,
    PrivacySettings,
    YasbSettings,
    get_model_api_key,
    load_local_settings,
    save_local_settings,
)
from daily_report.gui.data_provider import GuiDataProvider
from daily_report.reporter.deepseek_client import DeepSeekClient
from daily_report.service.material_service import MaterialService
from daily_report.service.overview_service import OverviewService
from daily_report.service.report_service import ReportService
from daily_report.service.timeline_service import TimelineService
from daily_report.storage.database import create_connection, init_database
from daily_report.storage.repositories.annotation_repository import AnnotationRepository


class GuiService:
    """Stable JSON-friendly facade for the Vue Web UI.

    The Web UI should depend on this class instead of reaching into storage
    modules or legacy QWidget pages directly.
    """

    def __init__(self, provider: GuiDataProvider | None = None):
        self.provider = provider or GuiDataProvider()
        self.report_service = ReportService(self.provider.db_path)
        self.timeline_service = TimelineService(self.provider.db_path)
        self.material_service = MaterialService(self.provider.db_path)
        self.overview_service = OverviewService(self.provider.db_path)

    def get_overview(self, target_date: str | None = None) -> dict[str, Any]:
        return self.overview_service.get_overview(target_date or self.provider.today())

    def get_timeline(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        filters = params.get("filters") if isinstance(params.get("filters"), dict) else params
        source_types = filters.get("source_types") or filters.get("sourceTypes")
        if isinstance(source_types, str):
            source_types = [source_types] if source_types else None
        events = self.timeline_service.list_timeline(
            date=str(params.get("date") or filters.get("date") or self.provider.today()),
            source_types=source_types,
            selected=_optional_bool(filters.get("selected")),
            sensitive=_optional_bool(filters.get("sensitive")),
            keyword=str(filters.get("keyword") or "").strip() or None,
            limit=int(filters.get("limit") or params.get("limit") or 500),
            sort_order=str(filters.get("sort_order") or filters.get("sortOrder") or "asc"),
        )
        return {"items": [event.to_dict() for event in events], "total": len(events)}

    def list_entries(
        self,
        source_type: str,
        target_date: str | None = None,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> dict[str, Any]:
        filters = filters or {}
        day = target_date or self.provider.today()
        page = max(1, int(page or 1))
        page_size = max(1, min(200, int(page_size or 30)))
        offset = (page - 1) * page_size
        table = self._source_table(source_type)
        time_column = self._source_time_column(source_type)
        clauses = ["date = ?"]
        params: list[Any] = [day]
        if self._table_has_column(table, "is_deleted"):
            clauses.append("is_deleted = 0")
        selected = _optional_bool(filters.get("selected"))
        if selected is not None and self._table_has_column(table, "is_selected"):
            clauses.append("is_selected = ?")
            params.append(int(selected))
        sensitive = _optional_bool(filters.get("sensitive"))
        if sensitive is not None and self._table_has_column(table, "is_sensitive"):
            clauses.append("is_sensitive = ?")
            params.append(int(sensitive))
        keyword = str(filters.get("keyword") or "").strip()
        if keyword:
            keyword_columns = self._keyword_columns(source_type)
            like = f"%{keyword}%"
            clauses.append("(" + " OR ".join(f"{column} LIKE ?" for column in keyword_columns) + ")")
            params.extend([like] * len(keyword_columns))

        sql_where = " AND ".join(clauses)
        conn = self.provider.connect()
        try:
            total_row = conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {sql_where}", tuple(params)).fetchone()
            rows = conn.execute(
                f"""
                SELECT *
                FROM {table}
                WHERE {sql_where}
                ORDER BY {time_column} DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                tuple([*params, page_size, offset]),
            ).fetchall()
            return {
                "items": [dict(row) for row in rows],
                "total": int(total_row["n"] if total_row else 0),
                "page": page,
                "page_size": page_size,
            }
        finally:
            conn.close()

    def get_entry_detail(self, source_type: str, entry_id: int) -> dict[str, Any] | None:
        return self.timeline_service.get_entry_detail(source_type, entry_id)

    def update_entry_selection(self, source_type: str, entry_id: int, selected: bool) -> dict[str, Any]:
        self.timeline_service.update_entry_selection(source_type, entry_id, selected)
        return {"source_type": source_type, "id": entry_id, "selected": selected}

    def mark_entry_deleted(self, source_type: str, entry_id: int) -> dict[str, Any]:
        self.timeline_service.mark_entry_deleted(source_type, entry_id)
        return {"source_type": source_type, "id": entry_id, "deleted": True}

    def update_entry_annotation(
        self,
        source_type: str,
        entry_id: int,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = payload or {}
        conn = create_connection(self.provider.db_path)
        try:
            init_database(conn)
            row = AnnotationRepository(conn).update_annotation(
                source_type=source_type,
                source_id=int(entry_id),
                category=payload.get("category"),
                note=payload.get("note"),
                importance=payload.get("importance"),
            )
            return dict(row)
        finally:
            conn.close()

    def get_report_materials(self, target_date: str | None = None) -> dict[str, Any]:
        day = target_date or self.provider.today()
        materials = self.material_service.build_materials(day, include_sensitive=False)
        return {
            "date": day,
            "items": [material.to_dict() for material in materials],
            "total": len(materials),
        }

    def build_prompt(self, target_date: str | None = None, template_name: str = "daily_standard") -> dict[str, Any]:
        day = target_date or self.provider.today()
        prompt = self.report_service.build_prompt(day, template_name=template_name)
        return {"date": day, "template_name": template_name, "prompt": prompt}

    def generate_report_sync(
        self,
        target_date: str | None = None,
        template_name: str = "daily_standard",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        result = self.report_service.generate_report(
            target_date=target_date or self.provider.today(),
            template_name=template_name,
            api_key=api_key,
            save=True,
        )
        return asdict(result)

    def get_latest_report(self, target_date: str | None = None) -> dict[str, Any] | None:
        record = self.report_service.get_latest_report(target_date or self.provider.today())
        return asdict(record) if record else None

    def list_reports(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        rows = self.report_service.list_reports(start_date=start_date, end_date=end_date)
        return {"items": [asdict(row) for row in rows], "total": len(rows)}

    def get_health(self) -> dict[str, Any]:
        overview = self.get_overview(self.provider.today())
        return {
            "ok": True,
            "database_path": str(self.provider.db_path),
            "collector_status": overview.get("collector_status"),
            "collector_states": overview.get("collector_states", []),
        }

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
        data["settings_path"] = str(self._settings_path())
        return data

    def save_settings(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = self._settings_from_payload(params or {}, load_local_settings())
        save_local_settings(settings)
        return self.get_settings()

    def test_model_connection(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = self._settings_from_payload(params or {}, load_local_settings())
        client = DeepSeekClient(
            api_key=settings.model.api_key.strip() or get_model_api_key(settings),
            model_name=settings.model.model_name,
            base_url=settings.model.base_url,
            temperature=settings.model.temperature,
            timeout_seconds=settings.model.timeout_seconds,
        )
        return {"message": client.test()}

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
    def _settings_path() -> Any:
        from daily_report.config.paths import get_runtime_paths

        return get_runtime_paths().local_settings_path

    @classmethod
    def _settings_from_payload(cls, data: dict[str, Any], base: LocalSettings) -> LocalSettings:
        return LocalSettings(
            model=cls._merge_section(ModelSettings, base.model, data.get("model", {})),
            collector=cls._merge_section(
                CollectorSettings,
                base.collector,
                data.get("collector", {}),
            ),
            privacy=cls._merge_section(PrivacySettings, base.privacy, data.get("privacy", {})),
            yasb=cls._merge_section(YasbSettings, base.yasb, data.get("yasb", {})),
            logging=cls._merge_section(LoggingSettings, base.logging, data.get("logging", {})),
        )

    @staticmethod
    def _merge_section(cls: type, base_obj: Any, raw: Any) -> Any:
        data = asdict(base_obj) if is_dataclass(base_obj) else {}
        allowed = {field.name for field in fields(cls)}
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key in allowed:
                    data[key] = value

        if cls is ModelSettings:
            data["api_key"] = _preserve_masked_secret(str(data.get("api_key") or ""), base_obj.api_key)
            data["max_prompt_chars"] = _clamp_int(data.get("max_prompt_chars"), 1000, 200000, base_obj.max_prompt_chars)
            data["timeout_seconds"] = _clamp_int(data.get("timeout_seconds"), 5, 300, base_obj.timeout_seconds)
            data["temperature"] = _clamp_float(data.get("temperature"), 0, 2, base_obj.temperature)
        elif cls is CollectorSettings:
            data["foreground_poll_interval_sec"] = _clamp_int(
                data.get("foreground_poll_interval_sec"),
                1,
                60,
                base_obj.foreground_poll_interval_sec,
            )
            data["edge_sync_interval_min"] = _clamp_int(
                data.get("edge_sync_interval_min"),
                1,
                120,
                base_obj.edge_sync_interval_min,
            )
        elif cls is LoggingSettings:
            level = str(data.get("level") or base_obj.level).upper()
            data["level"] = level if level in {"DEBUG", "INFO", "WARNING", "ERROR"} else base_obj.level
            data["retention_days"] = _clamp_int(data.get("retention_days"), 1, 3650, base_obj.retention_days)
        elif cls is PrivacySettings and not isinstance(data.get("sensitive_keywords"), list):
            data["sensitive_keywords"] = list(base_obj.sensitive_keywords)

        return cls(**data)

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

    @staticmethod
    def _source_table(source_type: str) -> str:
        normalized = "ai_prompt" if source_type == "ai" else str(source_type or "")
        mapping = {
            "app": "app_sessions",
            "browser": "browser_history_entries",
            "clipboard": "clipboard_entries",
            "ai_prompt": "ai_prompt_entries",
        }
        if normalized not in mapping:
            raise ValueError(f"Unsupported source type: {source_type}")
        return mapping[normalized]

    @staticmethod
    def _source_time_column(source_type: str) -> str:
        normalized = "ai_prompt" if source_type == "ai" else str(source_type or "")
        return {
            "app": "start_time",
            "browser": "visit_time",
            "clipboard": "last_seen_at",
            "ai_prompt": "timestamp",
        }.get(normalized, "id")

    @staticmethod
    def _keyword_columns(source_type: str) -> list[str]:
        normalized = "ai_prompt" if source_type == "ai" else str(source_type or "")
        return {
            "app": ["app_name", "process_name", "window_title"],
            "browser": ["title", "url", "domain", "search_query"],
            "clipboard": ["content_preview", "content"],
            "ai_prompt": ["platform", "page_title", "prompt_preview", "prompt_text"],
        }.get(normalized, ["id"])

    def _table_has_column(self, table_name: str, column_name: str) -> bool:
        conn = self.provider.connect()
        try:
            return column_name in {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})")}
        finally:
            conn.close()


def _clamp_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    return max(minimum, min(maximum, number))


def _clamp_float(value: Any, minimum: float, maximum: float, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return max(minimum, min(maximum, number))


def _preserve_masked_secret(value: str, fallback: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    if "*" in stripped and stripped.replace("*", "") in {"", fallback[:4] + fallback[-4:]}:
        return fallback
    return stripped


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "selected"}:
        return True
    if text in {"false", "0", "no", "unselected"}:
        return False
    return None
