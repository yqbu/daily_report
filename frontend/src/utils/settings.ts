import type { LocalSettingsPayload } from '../api/types'

export type LoggingLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
export type SettingsTab = 'collector' | 'privacy' | 'model' | 'system'

export interface YasbSettingsDraft {
  status_cli_command: string
  status_json_path: string
}

export interface SettingsDraft extends Omit<LocalSettingsPayload, 'yasb'> {
  yasb: YasbSettingsDraft
}

export function normalizeSettings(payload: LocalSettingsPayload): SettingsDraft {
  return {
    settings_path: payload.settings_path ?? payload.settingsPath,
    model: {
      provider: payload.model?.provider || 'deepseek',
      model_name: payload.model?.model_name || 'deepseek-chat',
      base_url: payload.model?.base_url || 'https://api.deepseek.com',
      api_key: payload.model?.api_key || '',
      max_prompt_chars: clampNumber(payload.model?.max_prompt_chars, 1000, 200000, 12000),
      timeout_seconds: clampNumber(payload.model?.timeout_seconds, 5, 300, 60),
      temperature: clampNumber(payload.model?.temperature, 0, 2, 0.3)
    },
    collector: {
      foreground_enabled: Boolean(payload.collector?.foreground_enabled ?? true),
      clipboard_enabled: Boolean(payload.collector?.clipboard_enabled ?? true),
      edge_history_enabled: Boolean(payload.collector?.edge_history_enabled ?? true),
      ai_prompt_enabled: Boolean(payload.collector?.ai_prompt_enabled ?? true),
      foreground_poll_interval_sec: clampNumber(payload.collector?.foreground_poll_interval_sec, 1, 60, 2),
      edge_sync_interval_min: clampNumber(payload.collector?.edge_sync_interval_min, 1, 120, 3)
    },
    privacy: {
      hide_sensitive_by_default: Boolean(payload.privacy?.hide_sensitive_by_default ?? true),
      sensitive_unselected_by_default: Boolean(payload.privacy?.sensitive_unselected_by_default ?? true),
      require_manual_confirm_before_llm: Boolean(payload.privacy?.require_manual_confirm_before_llm ?? true),
      clipboard_preview_only: Boolean(payload.privacy?.clipboard_preview_only ?? true),
      sensitive_keywords: Array.isArray(payload.privacy?.sensitive_keywords)
        ? payload.privacy.sensitive_keywords.map(String)
        : []
    },
    yasb: {
      status_cli_command: String(payload.yasb?.status_cli_command ?? 'daily-report status --json'),
      status_json_path: String(payload.yasb?.status_json_path ?? '')
    },
    logging: {
      level: normalizeLoggingLevel(payload.logging?.level),
      retention_days: clampNumber(payload.logging?.retention_days, 1, 3650, 30)
    }
  }
}

export function cloneSettings(settings: SettingsDraft): SettingsDraft {
  if (typeof structuredClone === 'function') {
    return structuredClone(settings)
  }

  return JSON.parse(JSON.stringify(settings)) as SettingsDraft
}

export function toBridgeSettings(settings: SettingsDraft): LocalSettingsPayload {
  return {
    settings_path: settings.settings_path,
    model: { ...settings.model },
    collector: { ...settings.collector },
    privacy: {
      ...settings.privacy,
      sensitive_keywords: [...settings.privacy.sensitive_keywords]
    },
    yasb: { ...settings.yasb },
    logging: { ...settings.logging }
  }
}

export function stableSettingsJson(settings: SettingsDraft): string {
  return JSON.stringify(toBridgeSettings(settings))
}

export function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  const number = Number(value)
  if (!Number.isFinite(number)) return fallback
  return Math.min(max, Math.max(min, number))
}

export function normalizeLoggingLevel(value: unknown): LoggingLevel {
  const level = String(value || 'INFO').toUpperCase()
  return ['DEBUG', 'INFO', 'WARNING', 'ERROR'].includes(level) ? (level as LoggingLevel) : 'INFO'
}

export function directoryFromPath(path: string | undefined): string {
  const value = path?.trim()
  if (!value) return ''
  const slashIndex = Math.max(value.lastIndexOf('/'), value.lastIndexOf('\\'))
  return slashIndex > 0 ? value.slice(0, slashIndex) : value
}

export function joinPath(directory: string, fileName: string): string {
  const trimmed = directory.trim()
  if (!trimmed) return fileName
  const separator = trimmed.includes('\\') ? '\\' : '/'
  return trimmed.endsWith('/') || trimmed.endsWith('\\') ? `${trimmed}${fileName}` : `${trimmed}${separator}${fileName}`
}

export function normalizeSettingsTab(value: unknown): SettingsTab {
  if (value === 'privacy' || value === 'model' || value === 'system') {
    return value
  }

  return 'collector'
}
