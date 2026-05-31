from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, fields, is_dataclass
from datetime import date as date_cls
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

from daily_report.config.local_settings import (
    CollectorSettings,
    LocalSettings,
    LoggingSettings,
    ModelSettings,
    PrivacySettings,
    YasbSettings,
    get_settings_path,
    get_model_api_key,
    load_local_settings,
    save_local_settings,
)
from daily_report.gui.data_provider import GuiDataProvider
from daily_report.reporter.deepseek_client import DeepSeekClient
from daily_report.service.app_profile_service import AppProfileService
from daily_report.service.category import infer_category_for_app
from daily_report.service.category import infer_category_for_browser
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
        self.app_profile_service = AppProfileService(self.provider.db_path)

    def get_overview(self, target_date: str | None = None) -> dict[str, Any]:
        return self.overview_service.get_overview(target_date or self.provider.today())

    def get_timeline(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        filters = params.get("filters") if isinstance(params.get("filters"), dict) else params
        limit = max(1, min(200, int(params.get("pageSize") or params.get("limit") or filters.get("limit") or 40)))
        offset = max(0, int(params.get("offset") or _cursor_offset(params.get("cursor")) or 0))
        events = self._timeline_events_for_params(params, filters)
        total = len(events)
        page_items = events[offset : offset + limit]
        next_offset = offset + limit
        return {
            "items": [event.to_dict() for event in page_items],
            "total": total,
            "offset": offset,
            "limit": limit,
            "nextCursor": str(next_offset) if next_offset < total else None,
            "hasMore": next_offset < total,
        }

    def _timeline_events_for_params(self, params: dict[str, Any], filters: dict[str, Any]) -> list[Any]:
        source_types = filters.get("source_types") or filters.get("sourceTypes")
        if isinstance(source_types, str):
            source_types = [source_types] if source_types else None
        sort_order = str(filters.get("sort_order") or filters.get("sortOrder") or "desc")
        categories = _normalize_category_filter(filters)
        events = []
        for day in _date_range_days(params, filters, self.provider.today()):
            events.extend(
                self.timeline_service.list_timeline(
                    date=day,
                    source_types=source_types,
                    selected=_optional_bool(filters.get("selected")),
                    sensitive=_optional_bool(filters.get("sensitive")),
                    category=categories,
                    keyword=str(filters.get("keyword") or "").strip() or None,
                    limit=100000,
                    offset=0,
                    sort_order=sort_order,
                )
            )
        reverse = sort_order.lower() == "desc"
        events.sort(key=lambda event: (event.start_time or "", event.source_id), reverse=reverse)
        return events

    def list_entries(
        self,
        source_type: str,
        target_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> dict[str, Any]:
        filters = filters or {}
        day = target_date or self.provider.today()
        page = max(1, int(page or 1))
        page_size = max(1, min(200, int(page_size or 30)))
        offset = (page - 1) * page_size
        if str(source_type or "") == "all":
            timeline = self.get_timeline(
                {
                    "date": day,
                    "startDate": start_date or day,
                    "endDate": end_date or day,
                    "filters": filters,
                    "offset": offset,
                    "limit": page_size,
                }
            )
            return {
                "items": timeline["items"],
                "total": timeline["total"],
                "page": page,
                "page_size": page_size,
            }
        table = self._source_table(source_type)
        time_column = self._source_time_column(source_type)
        range_days = _date_range_days(
            {
                "date": day,
                "startDate": start_date or day,
                "endDate": end_date or day,
            },
            {},
            self.provider.today(),
        )
        if len(range_days) > 1:
            placeholders = ",".join("?" for _ in range_days)
            clauses = [f"date IN ({placeholders})"]
            params: list[Any] = list(range_days)
        else:
            clauses = ["date = ?"]
            params = [range_days[0] if range_days else day]
        conn = self.provider.connect()
        try:
            columns = self._table_columns(conn, table)
            if "is_deleted" in columns:
                clauses.append("is_deleted = 0")
            selected = _optional_bool(filters.get("selected"))
            if selected is not None and "is_selected" in columns:
                clauses.append("is_selected = ?")
                params.append(int(selected))
            sensitive = _optional_bool(filters.get("sensitive"))
            if sensitive is not None and "is_sensitive" in columns:
                clauses.append("is_sensitive = ?")
                params.append(int(sensitive))
            keyword = str(filters.get("keyword") or "").strip()
            if keyword:
                keyword_columns = self._keyword_columns(source_type)
                like = f"%{keyword}%"
                clauses.append("(" + " OR ".join(f"{column} LIKE ?" for column in keyword_columns) + ")")
                params.extend([like] * len(keyword_columns))

            sql_where = " AND ".join(clauses)
            rows_for_total = conn.execute(
                f"""
                SELECT *
                FROM {table}
                WHERE {sql_where}
                ORDER BY {time_column} DESC, id DESC
                """,
                tuple(params),
            ).fetchall()
            annotation_repo = AnnotationRepository(conn)
            filtered_rows = [
                item
                for item in (self._merge_entry_row(annotation_repo, source_type, row) for row in rows_for_total)
                if self._matches_annotation_filters(item, filters)
            ]
            total = len(filtered_rows)
            page_items = filtered_rows[offset : offset + page_size]
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
                "items": page_items if (filters.get("category") or _requires_annotation_sensitive(source_type, sensitive)) else [
                    self._merge_entry_row(annotation_repo, source_type, row) for row in rows
                ],
                "total": total if (filters.get("category") or _requires_annotation_sensitive(source_type, sensitive)) else len(rows_for_total),
                "page": page,
                "page_size": page_size,
            }
        finally:
            conn.close()

    def get_entry_detail(
        self,
        source_type: str,
        entry_id: int,
        source_ids: list[int] | None = None,
    ) -> dict[str, Any] | None:
        return self.timeline_service.get_entry_detail(source_type, entry_id, source_ids=source_ids)

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
                is_sensitive_override=_optional_bool(payload.get("is_sensitive_override")),
                sensitivity_reason_override=payload.get("sensitivity_reason_override"),
            )
            return dict(row)
        finally:
            conn.close()

    def update_entry_sensitive(
        self,
        source_type: str,
        entry_id: int,
        sensitive: bool,
        reason: str | None = None,
        source_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_source_type(source_type)
        conn = create_connection(self.provider.db_path)
        try:
            init_database(conn)
            clean_reason = str(reason or "").strip() or None
            ids = [int(item) for item in (source_ids or [entry_id]) if int(item) > 0]
            if normalized == "clipboard":
                conn.executemany(
                    """
                    UPDATE clipboard_entries
                    SET is_sensitive = ?, sensitivity_reason = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                    """,
                    [(int(sensitive), clean_reason, item) for item in ids],
                )
                conn.commit()
            elif normalized == "ai_prompt":
                conn.executemany(
                    """
                    UPDATE ai_prompt_entries
                    SET is_sensitive = ?, sensitivity_reason = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                    """,
                    [(int(sensitive), clean_reason, item) for item in ids],
                )
                conn.commit()
            else:
                repo = AnnotationRepository(conn)
                for source_id in ids:
                    repo.update_sensitive_override(
                        source_type=normalized,
                        source_id=source_id,
                        sensitive=bool(sensitive),
                        reason=clean_reason,
                    )
            return {
                "source_type": normalized,
                "id": int(entry_id),
                "ids": ids,
                "is_sensitive": bool(sensitive),
                "sensitivity_reason": clean_reason,
            }
        finally:
            conn.close()

    def get_data_center_summary(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        filters = (params or {}).get("filters") if isinstance((params or {}).get("filters"), dict) else (params or {})
        items = [event.to_dict() for event in self._timeline_events_for_params(params or {}, filters)]
        by_source = Counter(str(item.get("source_type") or "") for item in items if isinstance(item, dict))
        sensitive_count = sum(1 for item in items if isinstance(item, dict) and bool(item.get("is_sensitive")))
        deleted_count = sum(1 for item in items if isinstance(item, dict) and bool(item.get("is_deleted")))
        category_counts = Counter(str(item.get("category") or "其他") for item in items if isinstance(item, dict))
        day_counts = Counter(
            str(item.get("start_time") or "")[:10]
            for item in items
            if isinstance(item, dict) and str(item.get("start_time") or "")[:10]
        )
        return {
            "total": len(items),
            "app": by_source.get("app", 0),
            "browser": by_source.get("browser", 0),
            "clipboard": by_source.get("clipboard", 0),
            "ai_prompt": by_source.get("ai_prompt", 0),
            "sensitive": sensitive_count,
            "deleted": deleted_count,
            "categories": [{"category": key, "count": value} for key, value in category_counts.most_common()],
            "days": [{"date": key, "count": day_counts[key]} for key in sorted(day_counts.keys(), reverse=True)],
        }

    def get_data_center_analytics(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        filters = params.get("filters") if isinstance(params.get("filters"), dict) else params
        chart_types = params.get("chartTypes") or params.get("chart_types") or []
        if isinstance(chart_types, str):
            chart_types = [chart_types]
        requested = set(chart_types) if chart_types else {
            "dailyRecordTrend",
            "hourlyHeatmap",
            "appDurationRanking",
            "domainRanking",
            "sensitiveSourceDistribution",
        }
        days = _date_range_days(params, filters, self.provider.today())
        charts: dict[str, Any] = {}
        summary = self.get_data_center_summary(params)
        conn = self.provider.connect()
        try:
            if "dailyRecordTrend" in requested:
                charts["dailyRecordTrend"] = self._analytics_daily_record_trend(conn, days)
            if "hourlyHeatmap" in requested:
                charts["hourlyHeatmap"] = self._analytics_hourly_heatmap(conn, days)
            if "appDurationRanking" in requested:
                charts["appDurationRanking"] = self._analytics_app_duration_ranking(conn, days)
            if "domainRanking" in requested:
                charts["domainRanking"] = self._analytics_domain_ranking(conn, days)
            if "sensitiveSourceDistribution" in requested:
                charts["sensitiveSourceDistribution"] = self._analytics_sensitive_source_distribution(conn, days)
        finally:
            conn.close()
        return {"summary": summary, "charts": charts}

    def list_app_profiles(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.app_profile_service.list_profiles(params)

    def save_app_profile(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.app_profile_service.save_profile(params)

    def reset_app_profile(self, params: dict[str, Any] | str | None = None) -> dict[str, Any]:
        return self.app_profile_service.reset_profile(params)

    def delete_app_records(self, params: dict[str, Any] | str | None = None) -> dict[str, Any]:
        return self.app_profile_service.delete_app_records(params)

    def list_app_categories(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.app_profile_service.list_categories(params)

    def save_app_category(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.app_profile_service.save_category(params)

    def delete_app_category(self, params: dict[str, Any] | str | None = None) -> dict[str, Any]:
        return self.app_profile_service.delete_category(params)

    def get_report_materials(self, params: str | dict[str, Any] | None = None) -> dict[str, Any]:
        if isinstance(params, dict):
            day = str(params.get("date") or "").strip() or self.provider.today()
            filters = params.get("filters") if isinstance(params.get("filters"), dict) else {}
            pagination = params.get("pagination") if isinstance(params.get("pagination"), dict) else {}
        else:
            day = params or self.provider.today()
            filters = {}
            pagination = {}

        source_types = filters.get("sourceTypes") or filters.get("source_types") or None
        if isinstance(source_types, str):
            source_types = [source_types] if source_types else None
        sensitive_filter = str(filters.get("sensitive") or "non_sensitive")
        sensitive = {"non_sensitive": False, "sensitive": True, "all": None}.get(sensitive_filter)
        category = str(filters.get("category") or "").strip() or None
        keyword = str(filters.get("keyword") or "").strip() or None

        all_filtered = self.timeline_service.list_timeline(
            date=day,
            source_types=source_types,
            selected=None,
            sensitive=sensitive,
            category=category,
            keyword=keyword,
            limit=100000,
            offset=0,
            sort_order="desc",
        )
        all_with_sensitive = self.timeline_service.list_timeline(
            date=day,
            source_types=source_types,
            selected=None,
            sensitive=None,
            category=category,
            keyword=keyword,
            limit=100000,
            offset=0,
            sort_order="desc",
        )
        offset = max(0, int(pagination.get("offset") or 0))
        limit = max(1, min(200, int(pagination.get("limit") or 50)))
        items = all_filtered[offset : offset + limit]
        selected_count = sum(1 for item in all_with_sensitive if item.is_selected and not item.is_sensitive)
        sensitive_excluded_count = sum(1 for item in all_with_sensitive if item.is_sensitive)
        pending_count = sum(1 for item in all_filtered if not item.is_selected)
        estimated_chars = sum(
            len((item.title or "") + (item.subtitle or "") + (item.content_preview or ""))
            for item in all_with_sensitive
            if item.is_selected and not item.is_sensitive
        )
        return {
            "summary": {
                "total_count": len(all_filtered),
                "selected_count": selected_count,
                "sensitive_excluded_count": sensitive_excluded_count,
                "pending_count": pending_count,
                "estimated_prompt_chars": estimated_chars,
            },
            "items": [self._material_candidate(item) for item in items],
            "hasMore": offset + limit < len(all_filtered),
        }

    def batch_update_entry_selection(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        selected = bool(params.get("selected"))
        raw_items = params.get("items") if isinstance(params.get("items"), list) else []
        updated = 0
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            source_type = str(item.get("sourceType") or item.get("source_type") or "")
            source_id = int(item.get("id") or item.get("source_id") or 0)
            if source_type and source_id:
                self.timeline_service.update_entry_selection(source_type, source_id, selected)
                updated += 1
        return {"ok": True, "updated": updated, "selected": selected}

    def build_prompt(self, params: str | dict[str, Any] | None = None, template_name: str = "daily_standard") -> dict[str, Any]:
        if isinstance(params, dict):
            day = str(params.get("date") or "").strip() or self.provider.today()
            template = str(params.get("templateName") or params.get("template_name") or template_name)
            extra_requirements = str(params.get("extraRequirements") or params.get("extra_requirements") or "").strip()
            output_focus = params.get("outputFocus") if isinstance(params.get("outputFocus"), list) else []
            options = params.get("options") if isinstance(params.get("options"), dict) else {}
        else:
            day = params or self.provider.today()
            template = template_name
            extra_requirements = ""
            output_focus = []
            options = {}
        prompt = self.report_service.build_prompt(
            day,
            template_name=template,
            extra_requirements=extra_requirements,
            output_focus=[str(item) for item in output_focus],
            options=options,
        )
        snapshot = self.material_service.build_snapshot(day, include_sensitive=False)
        return {
            "date": day,
            "template_name": template,
            "prompt": prompt,
            "prompt_text": prompt,
            "material_snapshot_json": json.dumps(snapshot, ensure_ascii=False),
            "estimated_tokens": max(1, len(prompt) // 4),
            "warnings": [],
        }

    def generate_report_sync(
        self,
        target_date: str | dict[str, Any] | None = None,
        template_name: str = "daily_standard",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(target_date, dict):
            options = target_date
            day = str(options.get("date") or "").strip() or self.provider.today()
            template_name = str(options.get("templateName") or options.get("template_name") or template_name)
            api_key = str(options.get("apiKey") or options.get("api_key") or "").strip() or None
            prompt_text = str(options.get("promptText") or options.get("prompt_text") or "").strip() or None
            extra_requirements = str(options.get("extraRequirements") or options.get("extra_requirements") or "").strip()
            output_focus = options.get("outputFocus") if isinstance(options.get("outputFocus"), list) else []
            prompt_options = options.get("options") if isinstance(options.get("options"), dict) else {}
        else:
            day = target_date or self.provider.today()
            prompt_text = None
            extra_requirements = ""
            output_focus = []
            prompt_options = {}
        result = self.report_service.generate_report(
            target_date=day,
            template_name=template_name,
            api_key=api_key,
            prompt_text=prompt_text,
            extra_requirements=extra_requirements,
            output_focus=[str(item) for item in output_focus],
            options=prompt_options,
            save=True,
        )
        return asdict(result)

    def save_report(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        report_id = self.report_service.save_report(
            target_date=str(params.get("date") or "").strip() or self.provider.today(),
            template_name=str(params.get("templateName") or params.get("template_name") or "daily_standard"),
            prompt_text=str(params.get("promptText") or params.get("prompt_text") or ""),
            report_markdown=str(params.get("reportMarkdown") or params.get("report_markdown") or ""),
            material_snapshot_json=str(params.get("materialSnapshotJson") or params.get("material_snapshot_json") or ""),
        )
        return {"report_id": report_id, "saved": True}

    def get_latest_report(self, target_date: str | None = None) -> dict[str, Any] | None:
        record = self.report_service.get_latest_report(target_date or self.provider.today())
        return asdict(record) if record else None

    def list_reports(
        self,
        start_date: str | dict[str, Any] | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(start_date, dict):
            params = start_date
            start = str(params.get("startDate") or params.get("start_date") or "").strip() or None
            end = str(params.get("endDate") or params.get("end_date") or "").strip() or None
            keyword = str(params.get("keyword") or "").strip().lower()
            template_name = str(params.get("templateName") or params.get("template_name") or "").strip()
            page = max(1, int(params.get("page") or 1))
            page_size = max(1, min(100, int(params.get("pageSize") or params.get("page_size") or 12)))
        else:
            start = start_date
            end = end_date
            keyword = ""
            template_name = ""
            page = 1
            page_size = 100
        rows = [asdict(row) for row in self.report_service.list_reports(start_date=start, end_date=end)]
        if keyword:
            rows = [
                row for row in rows
                if keyword in str(row.get("template_name") or "").lower()
                or keyword in str(row.get("report_markdown") or "").lower()
                or keyword in str(row.get("prompt_text") or "").lower()
            ]
        if template_name:
            rows = [row for row in rows if str(row.get("template_name") or "") == template_name]
        total = len(rows)
        offset = (page - 1) * page_size
        return {"items": rows[offset : offset + page_size], "total": total}

    def get_report_detail_by_id(self, params: dict[str, Any] | int | str | None = None) -> dict[str, Any] | None:
        report_id = params.get("id") if isinstance(params, dict) else params
        if report_id in (None, ""):
            return None
        record = self.report_service.get_report_detail(int(report_id))
        return asdict(record) if record else None

    def delete_report_by_id(self, params: dict[str, Any] | int | str | None = None) -> dict[str, Any]:
        report_id = params.get("id") if isinstance(params, dict) else params
        if report_id in (None, ""):
            raise ValueError("report id is required")
        self.report_service.delete_report(int(report_id))
        return {"ok": True, "id": int(report_id)}

    @staticmethod
    def _material_candidate(item: Any) -> dict[str, Any]:
        start = str(getattr(item, "start_time", "") or "")
        end = str(getattr(item, "end_time", "") or "")
        if start and end:
            time_range = f"{start[11:16]} - {end[11:16]}"
        else:
            time_range = start[11:16] if len(start) >= 16 else start
        meta = {
            "event_id": getattr(item, "event_id", ""),
            "source_ids": getattr(item, "source_ids", None),
            "item_count": getattr(item, "item_count", 1),
            "aggregate_kind": getattr(item, "aggregate_kind", None),
            "subtitle": getattr(item, "subtitle", ""),
        }
        return {
            "source_type": getattr(item, "source_type", ""),
            "source_id": int(getattr(item, "source_id", 0) or 0),
            "title": str(getattr(item, "title", "") or ""),
            "summary": str(getattr(item, "content_preview", "") or getattr(item, "subtitle", "") or ""),
            "time_range": time_range,
            "category": str(getattr(item, "category", "") or "其他"),
            "is_sensitive": bool(getattr(item, "is_sensitive", False)),
            "sensitivity_reason": None,
            "is_selected": bool(getattr(item, "is_selected", False)),
            "importance": 0,
            "meta": meta,
        }

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
            template_name=str(options.get("templateName") or options.get("template_name") or "daily_standard"),
            prompt_text=str(options.get("promptText") or options.get("prompt_text") or "").strip() or None,
            extra_requirements=str(options.get("extraRequirements") or options.get("extra_requirements") or "").strip(),
            output_focus=[str(item) for item in options.get("outputFocus", [])] if isinstance(options.get("outputFocus"), list) else [],
            options=options.get("options") if isinstance(options.get("options"), dict) else {},
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
        return self._settings_payload(settings, self._settings_path())

    def save_settings(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        settings = self._settings_from_payload(params, load_local_settings())
        settings_path = self._settings_path_from_payload(params) or self._settings_path()
        save_local_settings(settings, settings_path)
        return self._settings_payload(settings, self._settings_path())

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
    def _settings_path() -> Path:
        return get_settings_path()

    @staticmethod
    def _settings_payload(settings: LocalSettings, settings_path: Path) -> dict[str, Any]:
        data = asdict(settings)
        data["settings_path"] = str(settings_path)
        return data

    @staticmethod
    def _settings_path_from_payload(data: dict[str, Any]) -> Path | None:
        raw_path = str(data.get("settings_path") or data.get("settingsPath") or "").strip()
        if not raw_path:
            return None
        path = Path(raw_path).expanduser()
        return path if path.suffix.lower() == ".json" else path / "local_settings.json"

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
        days = [(today - timedelta(days=index)).isoformat() for index in range(6, -1, -1)]
        counts = self.provider.count_app_sessions_by_date(days)
        return [{"date": day, "count": counts.get(day, 0)} for day in days]

    def _search_app_sessions(
        self,
        day: str,
        keyword: str,
        app_name: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        sql = """
            FROM app_sessions a
            LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
            WHERE a.date = ?
              AND a.is_deleted = 0
              AND COALESCE(p.track_enabled, 1) = 1
        """
        params: list[Any] = [day]
        if app_name:
            sql += " AND COALESCE(NULLIF(p.display_name, ''), a.app_name) = ?"
            params.append(app_name)
        sql += " AND (a.app_name LIKE ? OR a.process_name LIKE ? OR a.window_title LIKE ? OR p.display_name LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like, like])
        conn = self.provider.connect()
        try:
            total_row = conn.execute(f"SELECT COUNT(*) AS n {sql}", tuple(params)).fetchone()
            rows = conn.execute(
                f"""
                SELECT a.*,
                       COALESCE(NULLIF(p.display_name, ''), a.app_name) AS display_app_name
                {sql}
                ORDER BY a.start_time ASC
                LIMIT ? OFFSET ?
                """,
                tuple([*params, limit, offset]),
            ).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                display_name = str(item.pop("display_app_name", "") or "").strip()
                if display_name:
                    item["app_name"] = display_name
                items.append(item)
            return items, int(total_row["n"] if total_row else 0)
        finally:
            conn.close()

    @staticmethod
    def _normalize_source_type(source_type: str) -> str:
        normalized = "ai_prompt" if source_type == "ai" else str(source_type or "")
        if normalized not in {"app", "browser", "clipboard", "ai_prompt"}:
            raise ValueError(f"Unsupported source type: {source_type}")
        return normalized

    def _merge_entry_row(
        self,
        annotation_repo: AnnotationRepository,
        source_type: str,
        row: Any,
    ) -> dict[str, Any]:
        normalized = self._normalize_source_type(source_type)
        item = dict(row)
        annotation = annotation_repo.get_annotation(normalized, int(item.get("id") or 0))
        annotation_data = dict(annotation) if annotation else {}
        item["source_type"] = normalized
        item["source_id"] = int(item.get("id") or 0)
        item["annotation"] = annotation_data or None
        if annotation_data.get("category"):
            item["category"] = annotation_data.get("category")
        elif normalized == "app":
            item["category"] = infer_category_for_app(str(item.get("process_name") or ""), str(item.get("window_title") or ""))
        elif normalized == "browser":
            item["category"] = infer_category_for_browser(
                str(item.get("title") or ""),
                str(item.get("url") or ""),
                item.get("is_search"),
                item.get("search_query"),
            )
        else:
            item["category"] = annotation_data.get("category")

        if normalized in {"app", "browser"}:
            item["is_sensitive"] = bool(annotation_data.get("is_sensitive_override") or 0)
            item["sensitivity_reason"] = annotation_data.get("sensitivity_reason_override")
        else:
            item["is_sensitive"] = bool(item.get("is_sensitive") or 0)
        item["importance"] = int(annotation_data.get("importance") or 0)
        item["note"] = annotation_data.get("note")
        return item

    @staticmethod
    def _matches_annotation_filters(item: dict[str, Any], filters: dict[str, Any]) -> bool:
        categories = _normalize_category_filter(filters)
        if categories and str(item.get("category") or "") not in categories:
            return False
        sensitive = _optional_bool(filters.get("sensitive"))
        if sensitive is not None and bool(item.get("is_sensitive")) is not sensitive:
            return False
        return True

    @staticmethod
    def _analytics_daily_record_trend(conn, days: list[str]) -> list[dict[str, Any]]:
        rows = []
        for day in days:
            rows.append(
                {
                    "date": day,
                    "app_count": _count_where(conn, "app_sessions", "date = ? AND is_deleted = 0", [day]),
                    "browser_count": _count_where(conn, "browser_history_entries", "date = ? AND is_deleted = 0", [day]),
                    "clipboard_count": _count_where(conn, "clipboard_entries", "date = ? AND is_deleted = 0", [day]),
                    "ai_prompt_count": _count_where(conn, "ai_prompt_entries", "date = ? AND is_deleted = 0", [day]),
                }
            )
        return rows

    @staticmethod
    def _analytics_hourly_heatmap(conn, days: list[str]) -> list[dict[str, Any]]:
        if not _service_table_exists(conn, "app_sessions"):
            return []
        rows = conn.execute(
            f"""
            SELECT date, substr(start_time, 12, 2) AS hour, SUM(active_duration_sec) AS active_duration_sec
            FROM app_sessions
            WHERE date IN ({','.join('?' for _ in days)}) AND is_deleted = 0
            GROUP BY date, hour
            """,
            tuple(days),
        ).fetchall()
        return [
            {
                "date": row["date"],
                "hour": int(row["hour"] or 0),
                "active_duration_sec": int(row["active_duration_sec"] or 0),
            }
            for row in rows
        ]

    @staticmethod
    def _analytics_app_duration_ranking(conn, days: list[str]) -> list[dict[str, Any]]:
        if not _service_table_exists(conn, "app_sessions"):
            return []
        rows = conn.execute(
            f"""
            SELECT COALESCE(NULLIF(p.display_name, ''), a.app_name, a.process_name) AS name,
                   SUM(a.active_duration_sec) AS active_duration_sec,
                   COUNT(*) AS session_count
            FROM app_sessions a
            LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
            WHERE a.date IN ({','.join('?' for _ in days)}) AND a.is_deleted = 0
            GROUP BY name
            ORDER BY active_duration_sec DESC
            LIMIT 12
            """,
            tuple(days),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _analytics_domain_ranking(conn, days: list[str]) -> list[dict[str, Any]]:
        if not _service_table_exists(conn, "browser_history_entries"):
            return []
        rows = conn.execute(
            f"""
            SELECT COALESCE(NULLIF(domain, ''), 'unknown') AS domain, COUNT(*) AS count
            FROM browser_history_entries
            WHERE date IN ({','.join('?' for _ in days)}) AND is_deleted = 0
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 12
            """,
            tuple(days),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _analytics_ai_platform_distribution(conn, days: list[str]) -> list[dict[str, Any]]:
        if not _service_table_exists(conn, "ai_prompt_entries"):
            return []
        rows = conn.execute(
            f"""
            SELECT COALESCE(NULLIF(platform, ''), 'AI') AS platform, COUNT(*) AS count
            FROM ai_prompt_entries
            WHERE date IN ({','.join('?' for _ in days)}) AND is_deleted = 0
            GROUP BY platform
            ORDER BY count DESC
            """,
            tuple(days),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _analytics_sensitive_source_distribution(conn, days: list[str]) -> list[dict[str, Any]]:
        values = [
            {
                "source_type": "clipboard",
                "count": _count_where(
                    conn,
                    "clipboard_entries",
                    f"date IN ({','.join('?' for _ in days)}) AND is_deleted = 0 AND is_sensitive = 1",
                    days,
                ),
            },
            {
                "source_type": "ai_prompt",
                "count": _count_where(
                    conn,
                    "ai_prompt_entries",
                    f"date IN ({','.join('?' for _ in days)}) AND is_deleted = 0 AND is_sensitive = 1",
                    days,
                ),
            },
        ]
        if _service_table_exists(conn, "entry_annotations"):
            for source_type in ("app", "browser"):
                values.append(
                    {
                        "source_type": source_type,
                        "count": _count_where(
                            conn,
                            "entry_annotations",
                            "source_type = ? AND is_sensitive_override = 1",
                            [source_type],
                        ),
                    }
                )
        return values

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

    @staticmethod
    def _table_columns(conn, table_name: str) -> set[str]:
        return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})")}


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


def _normalize_category_filter(filters: dict[str, Any]) -> list[str]:
    raw_categories = filters.get("categories")
    if isinstance(raw_categories, list):
        return [text for item in raw_categories if (text := str(item).strip())]
    category = str(filters.get("category") or "").strip()
    return [category] if category else []


def _cursor_offset(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _date_range_days(params: dict[str, Any], filters: dict[str, Any], fallback: str) -> list[str]:
    start_text = str(
        params.get("startDate")
        or params.get("start_date")
        or filters.get("startDate")
        or filters.get("start_date")
        or params.get("date")
        or filters.get("date")
        or fallback
    )[:10]
    end_text = str(
        params.get("endDate")
        or params.get("end_date")
        or filters.get("endDate")
        or filters.get("end_date")
        or params.get("date")
        or filters.get("date")
        or start_text
    )[:10]
    try:
        start = datetime.fromisoformat(start_text).date()
    except ValueError:
        start = datetime.fromisoformat(fallback[:10]).date()
    try:
        end = datetime.fromisoformat(end_text).date()
    except ValueError:
        end = start
    if end < start:
        start, end = end, start
    span = min((end - start).days, 366)
    return [(start + timedelta(days=index)).isoformat() for index in range(span + 1)]


def _requires_annotation_sensitive(source_type: str, sensitive: bool | None) -> bool:
    normalized = "ai_prompt" if source_type == "ai" else str(source_type or "")
    return sensitive is not None and normalized in {"app", "browser"}


def _service_table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _count_where(conn, table_name: str, where_sql: str, params: list[Any]) -> int:
    if not _service_table_exists(conn, table_name):
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {table_name} WHERE {where_sql}", tuple(params)).fetchone()
    return int(row["n"] if row else 0)
