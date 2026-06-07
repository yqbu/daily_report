import { apiGet, apiMode, apiPost } from './client'

export type RuntimeStatus = 'running' | 'stopped' | 'starting' | 'error' | 'warning' | 'unknown' | string
export type RuntimeRiskLevel = 'safe' | 'warning' | 'danger' | string
export type RuntimeDiagnosticLevel = 'info' | 'warning' | 'error'

export interface RuntimeProcessInfo {
  pid: number
  parent_pid: number | null
  role: string
  process_name: string | null
  exe_path: string | null
  cmdline: string[]
  cmdline_preview: string
  cwd: string | null
  username: string | null
  started_at: string | null
  cpu_percent: number | null
  memory_mb: number | null
  port: number | null
  status: string
  is_current_project: boolean
  is_registered: boolean
  is_orphan: boolean
  is_duplicate: boolean
  risk_level: RuntimeRiskLevel
  reason: string | null
}

export interface RuntimeComponentHealth {
  name: string
  display_name: string
  status: RuntimeStatus
  enabled: boolean
  last_success_at: string | null
  last_error_at: string | null
  last_error_message: string | null
  records_collected: number | null
  heartbeat_at: string | null
}

export interface RuntimeDiagnosticItem {
  code: string
  level: RuntimeDiagnosticLevel
  title: string
  message: string
  fixable: boolean
  action: string | null
}

export interface RuntimeSummary {
  api_status: RuntimeStatus
  api_pid: number | null
  api_port: number | null
  collector_status: RuntimeStatus
  collector_pid: number | null
  gui_status: RuntimeStatus
  database_status: RuntimeStatus
  yasb_status: RuntimeStatus
  duplicate_process_count: number
  orphan_process_count: number
  warning_count: number
  error_count: number
  updated_at: string
  processes: RuntimeProcessInfo[]
  components: RuntimeComponentHealth[]
  diagnostics: RuntimeDiagnosticItem[]
}

export interface RuntimeCleanupResult {
  dry_run: boolean
  force: boolean
  processes: RuntimeProcessInfo[]
  terminated?: Array<Record<string, unknown>>
  errors?: Array<Record<string, unknown>>
}

export async function getRuntimeSummary(): Promise<RuntimeSummary> {
  if (apiMode() === 'mock') return mockRuntimeSummary()
  return apiGet<RuntimeSummary>('/api/runtime/summary')
}

export async function getRuntimeProcesses(): Promise<RuntimeProcessInfo[]> {
  if (apiMode() === 'mock') return mockRuntimeSummary().processes
  return apiGet<RuntimeProcessInfo[]>('/api/runtime/processes')
}

export async function getRuntimeHealth(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { api_status: 'mock', collector_status: 'stopped' }
  return apiGet<Record<string, unknown>>('/api/runtime/health')
}

export async function runRuntimeDoctor(): Promise<RuntimeDiagnosticItem[]> {
  if (apiMode() === 'mock') return mockRuntimeSummary().diagnostics
  return apiPost<RuntimeDiagnosticItem[]>('/api/runtime/doctor', {})
}

export async function repairRuntime(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { ok: true, actions: [] }
  return apiPost<Record<string, unknown>>('/api/runtime/repair', { allow_kill: false })
}

export async function cleanupOrphans(dryRun: boolean, force: boolean): Promise<RuntimeCleanupResult> {
  if (apiMode() === 'mock') return { dry_run: dryRun, force, processes: mockRuntimeSummary().processes.filter((item) => item.is_orphan) }
  return apiPost<RuntimeCleanupResult>('/api/runtime/cleanup-orphans', { dry_run: dryRun, force })
}

export async function terminateProcess(pid: number): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>(`/api/runtime/processes/${pid}/terminate`, {})
}

export async function killProcess(pid: number): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>(`/api/runtime/processes/${pid}/kill`, {})
}

export async function startCollector(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { started: true }
  return apiPost<Record<string, unknown>>('/api/runtime/collector/start', {})
}

export async function stopCollector(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { ok: true }
  return apiPost<Record<string, unknown>>('/api/runtime/collector/stop', {})
}

export async function restartCollector(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { ok: true }
  return apiPost<Record<string, unknown>>('/api/runtime/collector/restart', {})
}

function mockRuntimeSummary(): RuntimeSummary {
  const now = new Date().toISOString()
  return {
    api_status: 'mock',
    api_pid: null,
    api_port: 8765,
    collector_status: 'stopped',
    collector_pid: null,
    gui_status: 'running',
    database_status: 'ok',
    yasb_status: 'not_configured',
    duplicate_process_count: 0,
    orphan_process_count: 0,
    warning_count: 1,
    error_count: 0,
    updated_at: now,
    processes: [],
    components: ['foreground', 'clipboard', 'edge_history', 'ai_prompt_receiver', 'browser_event_receiver'].map((name) => ({
      name,
      display_name: name.replace(/_/g, ' '),
      status: 'unknown',
      enabled: false,
      last_success_at: null,
      last_error_at: null,
      last_error_message: null,
      records_collected: null,
      heartbeat_at: null
    })),
    diagnostics: [
      {
        code: 'mock_mode',
        level: 'info',
        title: 'Browser mock mode',
        message: 'Start the Python API to inspect real local runtime processes.',
        fixable: false,
        action: null
      }
    ]
  }
}
