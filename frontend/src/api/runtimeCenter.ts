import { apiGet, apiPost } from './client'

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
  return apiGet<RuntimeSummary>('/api/runtime/summary')
}

export async function getRuntimeProcesses(full = false): Promise<RuntimeProcessInfo[]> {
  return apiGet<RuntimeProcessInfo[]>(`/api/runtime/processes?full=${String(full)}`)
}

export async function getRuntimeHealth(): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>('/api/runtime/health')
}

export async function runRuntimeDoctor(): Promise<RuntimeDiagnosticItem[]> {
  return apiPost<RuntimeDiagnosticItem[]>('/api/runtime/doctor', {})
}

export async function repairRuntime(): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>('/api/runtime/repair', { allow_kill: false })
}

export async function cleanupOrphans(dryRun: boolean, force: boolean): Promise<RuntimeCleanupResult> {
  return apiPost<RuntimeCleanupResult>('/api/runtime/cleanup-orphans', { dry_run: dryRun, force })
}

export async function terminateProcess(pid: number): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>(`/api/runtime/processes/${pid}/terminate`, {})
}

export async function killProcess(pid: number): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>(`/api/runtime/processes/${pid}/kill`, {})
}

export async function startCollector(): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>('/api/runtime/collector/start', {})
}

export async function stopCollector(): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>('/api/runtime/collector/stop', {})
}

export async function restartCollector(): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>('/api/runtime/collector/restart', {})
}
