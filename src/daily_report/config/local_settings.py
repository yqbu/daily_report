from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from daily_report.config.paths import get_runtime_paths


@dataclass
class ModelSettings:
    provider: str = 'deepseek'
    model_name: str = 'deepseek-chat'
    base_url: str = 'https://api.deepseek.com'
    api_key: str = ''
    max_prompt_chars: int = 12000
    timeout_seconds: int = 60
    temperature: float = 0.3


@dataclass
class AppSettings:
    model: ModelSettings


@dataclass
class CollectorSettings:
    foreground_enabled: bool = True
    clipboard_enabled: bool = True
    edge_history_enabled: bool = True
    ai_prompt_enabled: bool = True
    foreground_poll_interval_sec: int = 2
    edge_sync_interval_min: int = 3


@dataclass
class PrivacySettings:
    hide_sensitive_by_default: bool = True
    sensitive_unselected_by_default: bool = True
    require_manual_confirm_before_llm: bool = True
    clipboard_preview_only: bool = True
    sensitive_keywords: list[str] = field(
        default_factory=lambda: [
            'password',
            'token',
            'api_key',
            'secret',
            'sk-',
            '密码',
            '认证',
        ]
    )


@dataclass
class YasbSettings:
    status_json_path: str = ''
    status_cli_command: str = 'daily-report status --json'


@dataclass
class LoggingSettings:
    level: str = 'INFO'
    retention_days: int = 30


@dataclass
class LocalSettings:
    model: ModelSettings = field(default_factory=ModelSettings)
    collector: CollectorSettings = field(default_factory=CollectorSettings)
    privacy: PrivacySettings = field(default_factory=PrivacySettings)
    yasb: YasbSettings = field(default_factory=YasbSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)


def get_settings_path() -> Path:
    # 与当前项目的 data/daily_report.db 放在同级目录，便于本地单机部署。
    return get_runtime_paths().db_path.parent / "local_settings.json"


def load_local_settings(path: Path | None = None) -> LocalSettings:
    paths = get_runtime_paths()
    settings_path = path or paths.local_settings_path

    settings = LocalSettings()

    if not settings.yasb.status_json_path:
        settings.yasb.status_json_path = str(paths.status_json_path)

    if not settings_path.exists():
        save_local_settings(settings, settings_path)
        return settings

    with settings_path.open('r', encoding='utf-8') as f:
        raw = json.load(f)

    return _merge_settings(settings, raw)


def save_local_settings(
        settings: LocalSettings,
        path: Path | None = None,
        save_api_key: bool = True
) -> None:
    paths = get_runtime_paths()
    settings_path = path or paths.local_settings_path
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(settings)
    if not save_api_key:
        data["model"]["api_key"] = ""
    fd, tmp_name = tempfile.mkstemp(
        prefix=settings_path.name,
        suffix='.tmp',
        dir=str(settings_path.parent),
        text=True,
    )

    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Path(tmp_name).replace(settings_path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def get_model_api_key(settings: LocalSettings | None = None) -> str:
    """
    API Key 获取优先级：

    1. 环境变量 DEEPSEEK_API_KEY
    2. data/local_settings.json 中的 model.api_key
    """
    env_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if env_key:
        return env_key

    settings = settings or load_local_settings()
    return settings.model.api_key.strip()


def mask_api_key(api_key: str) -> str:
    if not api_key:
        return ''

    if len(api_key) <= 10:
        return '*' * len(api_key)

    return f"{api_key[:4]}{'*' * 8}{api_key[-4:]}"


def _merge_settings(default: LocalSettings, raw: dict[str, Any]) -> LocalSettings:
    return LocalSettings(
        model=_merge_dataclass(ModelSettings, default.model, raw.get('model', {})),
        collector=_merge_dataclass(CollectorSettings, default.collector, raw.get('collector', {})),
        privacy=_merge_dataclass(PrivacySettings, default.privacy, raw.get('privacy', {})),
        yasb=_merge_dataclass(YasbSettings, default.yasb, raw.get('yasb', {})),
        logging=_merge_dataclass(LoggingSettings, default.logging, raw.get('logging', {})),
    )


def _merge_dataclass(cls, default_obj, raw: dict[str, Any]):
    data = asdict(default_obj)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in data:
                data[key] = value
    return cls(**data)
