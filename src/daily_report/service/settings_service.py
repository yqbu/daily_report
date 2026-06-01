from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from daily_report.config.local_settings import (
    CollectorSettings,
    LoggingSettings,
    ModelSettings,
    PrivacySettings,
    YasbSettings,
    get_settings_path,
    load_local_settings,
    mask_api_key,
)


class SettingsService:
    """JSON-friendly settings service that preserves unknown config fields."""

    _sections = {
        'collector': CollectorSettings,
        'privacy': PrivacySettings,
        'model': ModelSettings,
        'yasb': YasbSettings,
        'logging': LoggingSettings,
    }

    def get_settings(self) -> dict[str, Any]:
        settings = load_local_settings()
        data = asdict(settings)
        data['settings_path'] = str(get_settings_path())
        data['system'] = {'logging': data.get('logging', {})}
        api_key = str(data.get('model', {}).get('api_key') or '')
        data['model']['api_key'] = mask_api_key(api_key)
        return data

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings_path = get_settings_path()
        raw = self._raw_settings(settings_path)
        current = asdict(load_local_settings())

        for section, cls in self._sections.items():
            raw_section = raw.get(section) if isinstance(raw.get(section), dict) else {}
            merged = dict(current.get(section, {}))
            merged.update(raw_section)
            incoming = self._incoming_section(section, payload)
            if incoming:
                allowed = {field.name for field in fields(cls)}
                for key, value in incoming.items():
                    if key not in allowed:
                        continue
                    if section == 'model' and key == 'api_key' and self._is_masked_secret(value):
                        continue
                    merged[key] = value
            raw[section] = merged

        self._write_json(settings_path, raw)
        return self.get_settings()

    @staticmethod
    def _incoming_section(section: str, payload: dict[str, Any]) -> dict[str, Any]:
        if section == 'logging':
            system = payload.get('system')
            if isinstance(system, dict) and isinstance(system.get('logging'), dict):
                return system['logging']
        value = payload.get(section)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _raw_settings(path: Path) -> dict[str, Any]:
        if not path.exists():
            return asdict(load_local_settings(path))
        try:
            with path.open('r', encoding='utf-8') as handle:
                value = json.load(handle)
        except (OSError, json.JSONDecodeError):
            value = {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix='.tmp', dir=str(path.parent), text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            Path(tmp_name).replace(path)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _is_masked_secret(value: Any) -> bool:
        text = str(value or '').strip()
        return bool(text) and '*' in text

