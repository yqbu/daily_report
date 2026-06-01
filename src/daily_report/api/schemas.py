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

