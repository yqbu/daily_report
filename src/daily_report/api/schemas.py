from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    ok: bool
    data: Any | None = None
    error: str | None = None
    code: str | None = None


class SelectionUpdateRequest(BaseModel):
    selected: bool


class DeletedUpdateRequest(BaseModel):
    deleted: bool


class EntryKeySelectionUpdateRequest(BaseModel):
    entry_key: str
    selected: bool


class EntryKeyDeletedUpdateRequest(BaseModel):
    entry_key: str
    deleted: bool


class EntryKeyAnnotationUpdateRequest(BaseModel):
    entry_key: str
    category: str | None = None
    note: str | None = None
    importance: int | None = None
    is_selected_override: bool | None = None
    is_sensitive_override: bool | None = None
    sensitivity_reason_override: str | None = None


class EntryKeySensitiveUpdateRequest(BaseModel):
    entry_key: str
    sensitive: bool | None = None
    reason: str | None = None


class BuildPromptRequest(BaseModel):
    date: str | None = None
    template_name: str = 'daily_standard'


class GenerateReportRequest(BaseModel):
    date: str | None = None
    template_name: str = 'daily_standard'
    save: bool = True


class SettingsUpdateRequest(BaseModel):
    collector: dict[str, Any] | None = None
    privacy: dict[str, Any] | None = None
    model: dict[str, Any] | None = None
    yasb: dict[str, Any] | None = None
    system: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None

    class Config:
        extra = 'allow'

