from __future__ import annotations

from pathlib import Path

from daily_report.sources.ai_prompt_source import AIPromptSourceAdapter
from daily_report.sources.aliases import normalize_source_type
from daily_report.sources.app_source import AppSourceAdapter
from daily_report.sources.base import SourceAdapter
from daily_report.sources.browser_source import BrowserSourceAdapter
from daily_report.sources.browser_event_source import BrowserEventSourceAdapter
from daily_report.sources.clipboard_source import ClipboardSourceAdapter


class SourceRegistry:
    def __init__(self):
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        self._adapters[adapter.source_type] = adapter

    def get(self, source_type: str) -> SourceAdapter:
        normalized = normalize_source_type(source_type)
        try:
            return self._adapters[normalized]
        except KeyError as exc:
            raise ValueError(f'Unsupported source_type: {source_type}') from exc

    def has(self, source_type: str) -> bool:
        try:
            normalized = normalize_source_type(source_type)
        except ValueError:
            return False
        return normalized in self._adapters

    def list_enabled(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def list_source_types(self) -> list[str]:
        return list(self._adapters.keys())


def create_default_source_registry(db_path: str | Path | None = None) -> SourceRegistry:
    registry = SourceRegistry()
    registry.register(AppSourceAdapter(db_path))
    registry.register(BrowserSourceAdapter(db_path))
    registry.register(ClipboardSourceAdapter(db_path))
    registry.register(AIPromptSourceAdapter(db_path))
    registry.register(BrowserEventSourceAdapter(db_path))
    return registry
