from __future__ import annotations

from daily_report.domain.category import (
    CATEGORIES,
    infer_category_for_ai_prompt,
    infer_category_for_app,
    infer_category_for_browser,
    infer_category_for_clipboard,
)

__all__ = [
    "CATEGORIES",
    "infer_category_for_ai_prompt",
    "infer_category_for_app",
    "infer_category_for_browser",
    "infer_category_for_clipboard",
]
