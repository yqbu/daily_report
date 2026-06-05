from __future__ import annotations

from typing import Any

from daily_report.reporter.material_card import MaterialCard
from daily_report.sources.base import RawEvent, SourceAdapter, TimelineEvent


class BilibiliSourceAdapter(SourceAdapter):
    """Placeholder for Phase 3 Bilibili viewing data.

    This adapter is intentionally not registered in the default registry and
    does not create or require a bilibili table.
    """

    source_type = 'bilibili'

    def list_raw_by_date(self, *args, **kwargs) -> list[RawEvent]:
        return []

    def get_raw_detail(self, source_id: int) -> dict[str, Any] | None:
        return None

    def normalize(self, raw_event: RawEvent) -> TimelineEvent:
        raise NotImplementedError('bilibili source is reserved for Phase 3')

    def to_material(self, event: TimelineEvent) -> MaterialCard | None:
        return None

    def update_selected(self, source_id: int, selected: bool) -> None:
        raise NotImplementedError('bilibili source is reserved for Phase 3')

    def update_deleted(self, source_id: int, deleted: bool) -> None:
        raise NotImplementedError('bilibili source is reserved for Phase 3')
