<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElEmpty,
  ElMessage,
  ElMessageBox,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTooltip
} from 'element-plus'

import {
  cleanupOrphans,
  getRuntimeProcesses,
  killProcess,
  repairRuntime,
  restartCollector,
  runRuntimeDoctor,
  startCollector,
  stopCollector,
  terminateProcess,
  getRuntimeSummary,
  type RuntimeCleanupResult,
  type RuntimeDiagnosticItem,
  type RuntimeProcessInfo,
  type RuntimeSummary
} from '../../api/runtimeCenter'

const emit = defineEmits<{
  refreshed: [summary: RuntimeSummary]
  busy: [name: string | null]
  loading: [active: boolean, text: string]
  cleanupPreviewChanged: [count: number]
}>()

const summary = shallowRef<RuntimeSummary | null>(null)
const diagnostics = shallowRef<RuntimeDiagnosticItem[]>([])
const cleanupPreview = shallowRef<RuntimeProcessInfo[]>([])
const fullProcesses = shallowRef<RuntimeProcessInfo[] | null>(null)
const actionBusy = shallowRef<string | null>(null)
const showDevelopmentProcesses = shallowRef(false)
const lastActionMessage = shallowRef('')
const repairResultText = shallowRef('')
const cleanupResultText = shallowRef('')

const collectorRunning = computed(() => summary.value?.collector_status === 'running')
const processes = computed(() => summary.value?.processes ?? [])
const developmentProcesses = computed(() => (fullProcesses.value ?? []).filter((process) => process.role === 'node' || process.role === 'tauri'))
const businessProcesses = computed(() => processes.value.filter((process) => process.role !== 'node' && process.role !== 'tauri'))
const visibleProcesses = computed(() => showDevelopmentProcesses.value && fullProcesses.value ? fullProcesses.value : businessProcesses.value)
const components = computed(() => summary.value?.components ?? [])
const visibleDiagnostics = computed(() => (diagnostics.value.length > 0 ? diagnostics.value : summary.value?.diagnostics ?? []))
const cleanupPreviewCount = computed(() => cleanupPreview.value.length)

const statusCards = computed(() => {
  const data = summary.value
  return [
    {
      key: 'api',
      label: 'API 服务',
      status: data?.api_status ?? 'unknown',
      meta: data?.api_pid ? `PID ${data.api_pid}${data.api_port ? ` / ${data.api_port}` : ''}` : '未检测到进程'
    },
    {
      key: 'collector',
      label: '采集器',
      status: data?.collector_status ?? 'unknown',
      meta: data?.collector_pid ? `PID ${data.collector_pid}` : '未检测到进程'
    },
    {
      key: 'database',
      label: '数据库',
      status: data?.database_status ?? 'unknown',
      meta: 'SQLite'
    },
    {
      key: 'yasb',
      label: 'YASB',
      status: data?.yasb_status ?? 'unknown',
      meta: 'status.json'
    },
    {
      key: 'orphans',
      label: '孤儿进程',
      status: String(data?.orphan_process_count ?? 0),
      meta: '仅清理可安全识别的进程'
    },
    {
      key: 'duplicates',
      label: '重复实例',
      status: String(data?.duplicate_process_count ?? 0),
      meta: '按逻辑运行实例判断'
    }
  ]
})

async function refreshSummary(text = '正在刷新运行状态…', manageLoading = true): Promise<void> {
  if (manageLoading) emit('loading', true, text)
  try {
    const data = await getRuntimeSummary()
    summary.value = data
    diagnostics.value = data.diagnostics
    lastActionMessage.value = `状态已刷新：${formatDateTime(data.updated_at)}`
    emit('refreshed', data)
  } finally {
    if (manageLoading) emit('loading', false, '')
  }
}

async function toggleDevelopmentProcesses(): Promise<void> {
  if (showDevelopmentProcesses.value) {
    showDevelopmentProcesses.value = false
    return
  }
  if (!fullProcesses.value) {
    setActionBusy('development-processes')
    emit('loading', true, '正在扫描系统进程…')
    try {
      fullProcesses.value = await getRuntimeProcesses(true)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : String(error))
      return
    } finally {
      emit('loading', false, '')
      setActionBusy(null)
    }
  }
  showDevelopmentProcesses.value = true
}

async function startCollectorAction(): Promise<void> {
  await runAction('start', async () => {
    const result = await startCollector()
    if (result.already_starting === true) return result
    const started = result.started !== false
    if (!started) {
      const tail = typeof result.log_tail === 'string' && result.log_tail.trim() ? `\n${result.log_tail.trim()}` : ''
      throw new Error(`采集器启动失败，退出码：${String(result.exit_code ?? '未知')}${tail}`)
    }
    return result
  }, '采集器启动命令已发送')
}

async function stopCollectorAction(): Promise<void> {
  await runAction('stop', stopCollector, '采集器已停止')
}

async function restartCollectorAction(): Promise<void> {
  await runAction('restart', async () => {
    const result = await restartCollector()
    const started = result.started as Record<string, unknown> | undefined
    if (started?.started === false) {
      const tail = typeof started.log_tail === 'string' && started.log_tail.trim() ? `\n${started.log_tail.trim()}` : ''
      throw new Error(`采集器重启失败，退出码：${String(started.exit_code ?? '未知')}${tail}`)
    }
    return result
  }, '采集器已重启')
}

async function handleDoctor(): Promise<void> {
  await runAction('doctor', async () => {
    diagnostics.value = await runRuntimeDoctor()
    return diagnostics.value
  }, '诊断已完成', { refresh: false, loadingText: '正在扫描系统进程…' })
}

async function handleRepair(): Promise<void> {
  await runAction('repair', async () => {
    const result = await repairRuntime()
    repairResultText.value = describeRepairResult(result)
    return result
  }, '安全修复已完成')
}

async function handleCleanupPreview(): Promise<void> {
  await runAction('cleanup-preview', async () => {
    const result = await cleanupOrphans(true, false)
    cleanupPreview.value = result.processes
    cleanupResultText.value = describeCleanupResult(result)
    emit('cleanupPreviewChanged', cleanupPreview.value.length)
    return result
  }, cleanupPreview.value.length > 0 ? '已生成清理预览' : '没有发现可清理的孤儿进程', {
    refresh: false,
    loadingText: '正在扫描系统进程…'
  })
}

async function handleCleanupExecute(): Promise<void> {
  if (cleanupPreview.value.length === 0) {
    await handleCleanupPreview()
    if (cleanupPreview.value.length === 0) return
  }

  const targetText = cleanupPreview.value.map((item) => `PID ${item.pid}：${item.cmdline_preview}`).join('\n')
  try {
    await ElMessageBox.confirm(targetText, '确认执行孤儿进程清理？', {
      type: 'warning',
      confirmButtonText: '执行清理',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--warning'
    })
  } catch {
    return
  }

  await runAction('cleanup-execute', async () => {
    const result = await cleanupOrphans(false, false)
    cleanupPreview.value = []
    cleanupResultText.value = describeCleanupResult(result)
    emit('cleanupPreviewChanged', 0)
    return result
  }, '清理执行完成')
}

async function handleTerminate(process: RuntimeProcessInfo): Promise<void> {
  try {
    await ElMessageBox.confirm(process.cmdline_preview, `确认终止 PID ${process.pid}？`, {
      type: 'warning',
      confirmButtonText: '终止',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  await runAction(`terminate-${process.pid}`, () => terminateProcess(process.pid), `已向 PID ${process.pid} 发送终止信号`)
}

async function handleKill(process: RuntimeProcessInfo): Promise<void> {
  try {
    await ElMessageBox.confirm(process.cmdline_preview, `确认强制结束 PID ${process.pid}？`, {
      type: 'error',
      confirmButtonText: '强制结束',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger'
    })
  } catch {
    return
  }
  await runAction(`kill-${process.pid}`, () => killProcess(process.pid), `已强制结束 PID ${process.pid}`)
}

interface RunActionOptions {
  refresh?: boolean
  loadingText?: string
}

async function runAction<T>(
  name: string,
  action: () => Promise<T>,
  message: string,
  options: RunActionOptions = {}
): Promise<T | null> {
  if (actionBusy.value) return null
  setActionBusy(name)
  emit('loading', true, options.loadingText ?? '正在执行运行操作…')
  try {
    const result = await action()
    ElMessage.success(message)
    lastActionMessage.value = message
    if (options.refresh !== false) {
      fullProcesses.value = null
      showDevelopmentProcesses.value = false
      emit('loading', true, '正在同步最新状态…')
      await refreshSummary('正在同步最新状态…', false)
    }
    return result
  } catch (error) {
    const text = error instanceof Error ? error.message : String(error)
    ElMessage.error(text)
    lastActionMessage.value = text
    return null
  } finally {
    emit('loading', false, '')
    setActionBusy(null)
  }
}

function setActionBusy(name: string | null): void {
  actionBusy.value = name
  emit('busy', name)
}

function canManageProcess(process: RuntimeProcessInfo): boolean {
  return (
    process.is_current_project &&
    process.pid !== summary.value?.api_pid &&
    process.role !== 'node' &&
    process.role !== 'tauri' &&
    process.role !== 'unknown_daily_report' &&
    process.role !== 'runtime_cli'
  )
}

function tagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  const value = status.toLowerCase()
  if (value === 'running' || value === 'ok' || value === '0' || value === 'safe' || value === 'info') return 'success'
  if (value === 'error' || value === 'danger') return 'danger'
  if (value === 'warning' || value === 'stale' || Number(value) > 0) return 'warning'
  return 'info'
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    running: '运行中',
    stopped: '未运行',
    starting: '启动中',
    error: '异常',
    warning: '需关注',
    unknown: '未知',
    ok: '正常',
    stale: '已过期',
    not_configured: '未配置',
    safe: '安全',
    danger: '危险',
    info: '提示'
  }
  return map[status.toLowerCase()] ?? status
}

function roleText(role: string): string {
  const map: Record<string, string> = {
    api: 'API 服务',
    collector: '采集器',
    gui: '桌面窗口',
    tauri: 'Tauri 外壳',
    node: '前端开发服务',
    yasb_script: 'YASB 脚本',
    runtime_cli: '运行时命令',
    unknown_daily_report: 'Daily Report 相关'
  }
  return map[role] ?? role
}

function componentText(name: string): string {
  const map: Record<string, string> = {
    foreground: '前台应用',
    clipboard: '剪贴板',
    edge_history: 'Edge 历史',
    ai_prompt: 'AI Prompt',
    ai_prompt_receiver: 'AI Prompt 接收器',
    browser_event_receiver: '浏览器事件接收器',
    cleanup_worker: '清理任务',
    status_json_worker: '状态文件写入'
  }
  return map[name] ?? name
}

function riskText(risk: string): string {
  const map: Record<string, string> = {
    safe: '安全',
    warning: '需确认',
    danger: '危险'
  }
  return map[risk] ?? risk
}

function diagnosticTitle(item: RuntimeDiagnosticItem): string {
  const map: Record<string, string> = {
    api_not_running: 'API 健康检查未通过',
    collector_not_running: '采集器未运行',
    api_port_occupied: 'API 端口被占用',
    duplicate_processes: '发现重复运行实例',
    orphan_processes: '发现孤儿进程',
    stale_lock: '采集器锁文件已过期',
    database_error: '数据库检查失败',
    database_warning: '数据库存在警告',
    yasb_status_stale: 'YASB 状态文件未更新',
    runtime_ok: '运行时状态正常'
  }
  return map[item.code] ?? item.title
}

function diagnosticMessage(item: RuntimeDiagnosticItem): string {
  if (item.code === 'collector_not_running') {
    return '未发现运行中的采集器进程。如果数据库里仍显示 running，可以先点“安全修复”，再启动采集器。'
  }
  if (item.code === 'duplicate_processes') {
    return '检测到多个同类运行实例，请确认是否为预期；可先查看下方进程表再处理。'
  }
  if (item.code === 'orphan_processes') {
    return '检测到父进程已退出的相关子进程。先使用“预览清理”确认目标，再执行清理。'
  }
  if (item.code === 'runtime_ok') {
    return '没有发现需要处理的运行时警告。'
  }
  return item.message
}

function actionText(action: string | null): string {
  const map: Record<string, string> = {
    start_collector: '启动采集器',
    cleanup_orphans: '预览或执行清理',
    repair: '安全修复'
  }
  return action ? map[action] ?? action : ''
}

function describeRepairResult(result: Record<string, unknown>): string {
  const actions = Array.isArray(result.actions) ? result.actions as Array<Record<string, unknown>> : []
  if (actions.length === 0) return '没有需要修复的运行时状态。'
  const lines = actions.map((action) => {
    const name = String(action.action ?? 'unknown')
    const count = Number(action.count ?? 0)
    if (name === 'cleanup_stale_runtime_processes') return `清理已退出进程记录：${count} 条`
    if (name === 'mark_stale_collector_states_stopped') return `修正采集器残留运行态：${count} 条`
    if (name === 'remove_stale_lock') return `移除过期锁文件：PID ${String(action.pid ?? '-')}`
    return `${name}：${count}`
  })
  return lines.join('；')
}

function describeCleanupResult(result: RuntimeCleanupResult): string {
  const count = result.processes.length
  if (result.dry_run) return count > 0 ? `预览到 ${count} 个可清理的孤儿进程。` : '没有发现可清理的孤儿进程。'
  const terminated = result.terminated?.length ?? 0
  const errors = result.errors?.length ?? 0
  return `已终止 ${terminated} 个进程${errors > 0 ? `，失败 ${errors} 个` : ''}。`
}

function formatNumber(value: number | null): string {
  return value === null ? '-' : String(value)
}

function formatDateTime(value: string | null): string {
  if (!value) return '-'
  return value.replace('T', ' ')
}

defineExpose({
  refreshSummary,
  startCollectorAction,
  stopCollectorAction,
  restartCollectorAction,
  handleDoctor,
  handleRepair,
  handleCleanupPreview,
  handleCleanupExecute
})

onMounted(() => {
  void refreshSummary()
})
</script>

<template>
  <div class="runtime-center">
    <ElCard shadow="never" class="runtime-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>运行概览</h2>
            <p>当前状态、端口、采集器和数据库健康度。</p>
          </div>
          <ElTag :type="summary?.error_count ? 'danger' : summary?.warning_count ? 'warning' : 'success'" effect="light">
            {{ summary?.error_count ? '存在错误' : summary?.warning_count ? '需要关注' : '状态正常' }}
          </ElTag>
        </div>
      </template>

      <div class="status-grid">
        <article v-for="card in statusCards" :key="card.key" class="status-card">
          <span class="status-label">{{ card.label }}</span>
          <ElTag :type="tagType(card.status)" effect="light">{{ statusText(card.status) }}</ElTag>
          <span class="status-meta">{{ card.meta }}</span>
        </article>
      </div>

      <p v-if="lastActionMessage" class="runtime-message">{{ lastActionMessage }}</p>
    </ElCard>

    <ElCard shadow="never" class="runtime-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>运行操作说明</h2>
            <p>这些操作只处理 Daily Report 当前项目的运行状态。</p>
          </div>
        </div>
      </template>

      <ElAlert type="info" :closable="false" show-icon>
        <template #title>安全修复、预览清理、执行清理的作用</template>
        <ul class="operation-notes">
          <li><strong>安全修复</strong>：清理已退出的运行记录，移除过期锁文件，并把没有进程支撑的采集器 running 状态改为 stopped；不会杀进程。</li>
          <li><strong>预览清理</strong>：只扫描父进程已退出、且能安全识别的孤儿进程，不做终止操作。</li>
          <li><strong>执行清理</strong>：只终止预览列表中的孤儿进程；没有预览目标时不会执行。</li>
        </ul>
      </ElAlert>

      <div v-if="repairResultText || cleanupResultText" class="result-strip">
        <span v-if="repairResultText">{{ repairResultText }}</span>
        <span v-if="cleanupResultText">{{ cleanupResultText }}</span>
      </div>
    </ElCard>

    <ElCard shadow="never" class="runtime-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>运行进程</h2>
            <p>
              {{ businessProcesses.length }} 个业务进程
              <span v-if="fullProcesses">，另有 {{ developmentProcesses.length }} 个开发工具进程</span>
              <span v-else>，开发进程按需加载</span>
            </p>
          </div>
          <ElButton
            size="small"
            plain
            :loading="actionBusy === 'development-processes'"
            @click="toggleDevelopmentProcesses"
          >
            {{ showDevelopmentProcesses ? '隐藏开发进程' : fullProcesses ? `显示开发进程 (${developmentProcesses.length})` : '显示开发进程' }}
          </ElButton>
        </div>
      </template>

      <ElTable v-if="visibleProcesses.length > 0" :data="visibleProcesses" class="runtime-table" border>
        <ElTableColumn label="角色" min-width="120">
          <template #default="{ row }">
            {{ roleText(row.role) }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="pid" label="PID" width="90" />
        <ElTableColumn label="父 PID" width="90">
          <template #default="{ row }">{{ row.parent_pid ?? '-' }}</template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="100">
          <template #default="{ row }">
            <ElTag :type="tagType(row.status)" effect="plain">{{ statusText(row.status) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="CPU" width="80">
          <template #default="{ row }">{{ formatNumber(row.cpu_percent) }}</template>
        </ElTableColumn>
        <ElTableColumn label="内存 MB" width="100">
          <template #default="{ row }">{{ formatNumber(row.memory_mb) }}</template>
        </ElTableColumn>
        <ElTableColumn label="端口" width="90">
          <template #default="{ row }">{{ row.port ?? '-' }}</template>
        </ElTableColumn>
        <ElTableColumn label="启动时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="命令行" min-width="280">
          <template #default="{ row }">
            <ElTooltip :content="row.cmdline_preview" placement="top" :show-after="300">
              <span class="cmdline-preview">{{ row.cmdline_preview }}</span>
            </ElTooltip>
          </template>
        </ElTableColumn>
        <ElTableColumn label="风险" width="110">
          <template #default="{ row }">
            <ElTooltip :disabled="!row.reason" :content="row.reason ?? ''" placement="top">
              <ElTag :type="tagType(row.risk_level)" effect="plain">{{ riskText(row.risk_level) }}</ElTag>
            </ElTooltip>
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" fixed="right" width="170">
          <template #default="{ row }">
            <div class="row-actions">
              <ElButton size="small" :disabled="!canManageProcess(row)" :loading="actionBusy === `terminate-${row.pid}`" @click="handleTerminate(row)">
                终止
              </ElButton>
              <ElButton size="small" type="danger" :disabled="!canManageProcess(row)" :loading="actionBusy === `kill-${row.pid}`" @click="handleKill(row)">
                强制
              </ElButton>
            </div>
          </template>
        </ElTableColumn>
      </ElTable>
      <ElEmpty v-else description="未检测到 Daily Report 相关进程" />
    </ElCard>

    <ElCard shadow="never" class="runtime-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>采集器组件</h2>
            <p>{{ components.length }} 个组件状态</p>
          </div>
        </div>
      </template>

      <ElTable v-if="components.length > 0" :data="components" class="runtime-table" border>
        <ElTableColumn label="组件" min-width="150">
          <template #default="{ row }">{{ componentText(row.name) }}</template>
        </ElTableColumn>
        <ElTableColumn label="启用" width="80">
          <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="110">
          <template #default="{ row }">
            <ElTag :type="tagType(row.status)" effect="plain">{{ statusText(row.status) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="最近成功" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.last_success_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="最近错误" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.last_error_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="记录数" width="90">
          <template #default="{ row }">{{ row.records_collected ?? '-' }}</template>
        </ElTableColumn>
        <ElTableColumn label="心跳" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.heartbeat_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="错误信息" min-width="220">
          <template #default="{ row }">
            <span class="cmdline-preview">{{ row.last_error_message || '-' }}</span>
          </template>
        </ElTableColumn>
      </ElTable>
      <ElEmpty v-else description="暂无采集器组件状态" />
    </ElCard>

    <ElCard shadow="never" class="runtime-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>诊断结果</h2>
            <p>{{ visibleDiagnostics.length }} 条诊断信息</p>
          </div>
        </div>
      </template>

      <div class="diagnostic-list">
        <article v-for="item in visibleDiagnostics" :key="item.code" class="diagnostic-item">
          <ElTag :type="tagType(item.level)" effect="light">{{ statusText(item.level) }}</ElTag>
          <div class="diagnostic-copy">
            <strong>{{ diagnosticTitle(item) }}</strong>
            <span>{{ diagnosticMessage(item) }}</span>
            <small v-if="item.fixable">建议操作：{{ actionText(item.action) }}</small>
          </div>
        </article>
      </div>
    </ElCard>

    <ElCard shadow="never" class="runtime-card">
      <template #header>
        <div class="card-heading">
          <div>
            <h2>清理预览</h2>
            <p>{{ cleanupPreviewCount }} 个待清理目标</p>
          </div>
        </div>
      </template>

      <ElTable v-if="cleanupPreview.length > 0" :data="cleanupPreview" class="runtime-table" border>
        <ElTableColumn prop="pid" label="PID" width="90" />
        <ElTableColumn label="角色" min-width="130">
          <template #default="{ row }">{{ roleText(row.role) }}</template>
        </ElTableColumn>
        <ElTableColumn label="命令行" min-width="360">
          <template #default="{ row }">
            <span class="cmdline-preview">{{ row.cmdline_preview }}</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="原因" min-width="180">
          <template #default="{ row }">{{ row.reason ?? '父进程已退出' }}</template>
        </ElTableColumn>
      </ElTable>
      <ElEmpty v-else description="先点击顶栏的“预览清理”查看可清理目标" />
    </ElCard>
  </div>
</template>

<style scoped>
.runtime-center {
  position: relative;
  isolation: isolate;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  overflow: visible;
  background: #fbfcfd;
}

.runtime-card {
  flex: 0 0 auto;
  overflow: visible;
  border-radius: 8px;
}

.runtime-card :deep(.el-card__header) {
  padding: 14px 16px;
}

.runtime-card :deep(.el-card__body) {
  padding: 16px;
  overflow: visible;
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-heading h2,
.card-heading p,
.runtime-message,
.operation-notes {
  margin: 0;
}

.card-heading h2 {
  color: #172033;
  font-size: 15px;
  font-weight: 760;
  line-height: 1.25;
  letter-spacing: 0;
}

.card-heading p,
.runtime-message,
.status-meta,
.diagnostic-copy span,
.diagnostic-copy small {
  color: #667085;
  font-size: 12px;
  line-height: 1.45;
}

.card-heading p {
  margin-top: 4px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(118px, 1fr));
  gap: 10px;
}

.status-card {
  min-width: 0;
  min-height: 92px;
  display: grid;
  align-content: start;
  gap: 9px;
  padding: 12px;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  background: #ffffff;
}

.status-label {
  color: #344054;
  font-size: 12px;
  font-weight: 760;
}

.runtime-message {
  margin-top: 12px;
}

.operation-notes {
  display: grid;
  gap: 6px;
  padding-left: 18px;
  color: #344054;
  font-size: 12px;
  line-height: 1.55;
}

.result-strip {
  display: grid;
  gap: 6px;
  margin-top: 12px;
  color: #344054;
  font-size: 12px;
}

.runtime-table {
  width: 100%;
}

.runtime-table :deep(.el-table__cell) {
  vertical-align: top;
}

.cmdline-preview {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

.row-actions {
  display: flex;
  gap: 6px;
  white-space: nowrap;
}

.diagnostic-list {
  display: grid;
  gap: 8px;
}

.diagnostic-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  background: #ffffff;
}

.diagnostic-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.diagnostic-copy strong {
  color: #172033;
  font-size: 13px;
}

@media (max-width: 1180px) {
  .status-grid {
    grid-template-columns: repeat(3, minmax(118px, 1fr));
  }
}

@media (max-width: 720px) {
  .runtime-center {
    padding: 12px;
  }

  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
