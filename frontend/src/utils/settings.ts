import type { LocalSettingsPayload } from '../api/types'

export interface SettingsDraft {
  settings_path: string
  model: LocalSettingsPayload['model']
  collector: LocalSettingsPayload['collector']
  privacy: LocalSettingsPayload['privacy']
  yasb: {
    status_json_path: string
    status_cli_command: string
  }
  logging: LocalSettingsPayload['logging']
}

export function normalizeSettings(payload: Partial<LocalSettingsPayload>): SettingsDraft {
  return {
    settings_path: String(payload.settings_path || payload.settingsPath || ''),
    model: {
      provider: String(payload.model?.provider || 'deepseek'),
      model_name: String(payload.model?.model_name || 'deepseek-chat'),
      base_url: String(payload.model?.base_url || 'https://api.deepseek.com'),
      api_key: String(payload.model?.api_key || ''),
      max_prompt_chars: Number(payload.model?.max_prompt_chars || 12000),
      timeout_seconds: Number(payload.model?.timeout_seconds || 60),
      temperature: Number(payload.model?.temperature ?? 0.3)
    },
    collector: {
      foreground_enabled: Boolean(payload.collector?.foreground_enabled ?? true),
      clipboard_enabled: Boolean(payload.collector?.clipboard_enabled ?? true),
      edge_history_enabled: Boolean(payload.collector?.edge_history_enabled ?? true),
      ai_prompt_enabled: Boolean(payload.collector?.ai_prompt_enabled ?? true),
      foreground_poll_interval_sec: Number(payload.collector?.foreground_poll_interval_sec || 2),
      edge_sync_interval_min: Number(payload.collector?.edge_sync_interval_min || 3)
    },
    privacy: {
      hide_sensitive_by_default: Boolean(payload.privacy?.hide_sensitive_by_default ?? true),
      sensitive_unselected_by_default: Boolean(payload.privacy?.sensitive_unselected_by_default ?? true),
      require_manual_confirm_before_llm: Boolean(payload.privacy?.require_manual_confirm_before_llm ?? true),
      clipboard_preview_only: Boolean(payload.privacy?.clipboard_preview_only ?? true),
      sensitive_keywords: [...(payload.privacy?.sensitive_keywords || [])]
    },
    yasb: {
      status_json_path: String(payload.yasb?.status_json_path || ''),
      status_cli_command: String(payload.yasb?.status_cli_command || 'daily-report status --json')
    },
    logging: {
      level: String(payload.logging?.level || 'INFO'),
      retention_days: Number(payload.logging?.retention_days || 30)
    }
  }
}

export function cloneSettings(settings: SettingsDraft): SettingsDraft {
  return JSON.parse(JSON.stringify(settings)) as SettingsDraft
}

export function stableSettingsJson(settings: SettingsDraft): string {
  return JSON.stringify(sortObject(settings))
}

export function toApiSettings(settings: SettingsDraft): LocalSettingsPayload {
  return cloneSettings(settings) as LocalSettingsPayload
}

export function directoryFromPath(path: string): string {
  const value = String(path || '').replace(/\\/g, '/')
  const index = value.lastIndexOf('/')
  return index >= 0 ? value.slice(0, index) : value
}

export function joinPath(directory: string, fileName: string): string {
  const separator = directory.includes('\\') ? '\\' : '/'
  return `${directory.replace(/[\\/]+$/, '')}${separator}${fileName}`
}

function sortObject(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortObject)
  if (!value || typeof value !== 'object') return value

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, entry]) => [key, sortObject(entry)])
  )
}
