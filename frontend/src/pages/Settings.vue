<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Connection,
  Cpu,
  DataAnalysis,
  FolderOpened,
  Lock,
  Monitor,
  Plus,
  Refresh
} from '@element-plus/icons-vue'

import { callBridge, callBridgeJob, callTypedBridge } from '../api/bridge'
import type { LocalSettingsPayload } from '../api/types'
import SettingsField from '../components/settings/SettingsField.vue'
import SettingsSection from '../components/settings/SettingsSection.vue'
import { useAppStore } from '../stores/app'

type LoggingLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
type SettingsTab = 'collector' | 'privacy' | 'model' | 'system'

interface YasbSettingsDraft {
  status_cli_command: string
  status_json_path: string
}

interface SettingsDraft extends Omit<LocalSettingsPayload, 'yasb'> {
  yasb: YasbSettingsDraft
}

const appStore = useAppStore()
const savedSettings = ref<SettingsDraft | null>(null)
const draftSettings = ref<SettingsDraft | null>(null)
const loading = shallowRef(false)
const saving = shallowRef(false)
const testingConnection = shallowRef(false)
const settingsError = shallowRef('')
const operationMessage = shallowRef('')
const keywordInput = shallowRef('')
const settingsLoadRequestId = shallowRef(0)
const activeSettingsTab = shallowRef<SettingsTab>('collector')

const collectorCards = computed(() => {
  const settings = draftSettings.value
  if (!settings) return []

  return [
    {
      key: 'foreground_enabled',
      title: '前台应用',
      description: '记录活跃窗口、进程和停留时间。',
      enabled: settings.collector.foreground_enabled,
      update: (value: boolean) => {
        settings.collector.foreground_enabled = value
      }
    },
    {
      key: 'clipboard_enabled',
      title: '剪贴板',
      description: '保留剪贴板摘要用于日报素材筛选。',
      enabled: settings.collector.clipboard_enabled,
      update: (value: boolean) => {
        settings.collector.clipboard_enabled = value
      }
    },
    {
      key: 'edge_history_enabled',
      title: 'Edge 历史',
      description: '同步浏览记录、标题和搜索线索。',
      enabled: settings.collector.edge_history_enabled,
      update: (value: boolean) => {
        settings.collector.edge_history_enabled = value
      }
    },
    {
      key: 'ai_prompt_enabled',
      title: 'AI Prompt',
      description: '接收来自扩展或页面的 Prompt 片段。',
      enabled: settings.collector.ai_prompt_enabled,
      update: (value: boolean) => {
        settings.collector.ai_prompt_enabled = value
      }
    }
  ]
})

const hasUnsavedChanges = computed(() => {
  if (!savedSettings.value || !draftSettings.value) return false
  return stableSettingsJson(savedSettings.value) !== stableSettingsJson(draftSettings.value)
})

const topBarSaveStatus = computed(() => {
  if (saving.value) {
    return { text: '保存中', tone: 'saving' as const }
  }

  if (settingsError.value) {
    return { text: '设置异常', tone: 'error' as const }
  }

  if (hasUnsavedChanges.value) {
    return { text: '有未保存更改', tone: 'dirty' as const }
  }

  return { text: operationMessage.value || '已保存', tone: 'saved' as const }
})

async function loadSettings(): Promise<void> {
  const requestId = settingsLoadRequestId.value + 1
  settingsLoadRequestId.value = requestId
  loading.value = true
  settingsError.value = ''

  try {
    const payload = await callTypedBridge('getSettings', {})
    if (requestId !== settingsLoadRequestId.value) return
    const normalized = normalizeSettings(payload)
    savedSettings.value = cloneSettings(normalized)
    draftSettings.value = cloneSettings(normalized)
    flashOperationMessage('配置已加载')
  } catch (error) {
    if (requestId !== settingsLoadRequestId.value) return
    showSettingsError(error)
  } finally {
    if (requestId === settingsLoadRequestId.value) {
      loading.value = false
    }
  }
}

async function saveSettings(): Promise<void> {
  if (!draftSettings.value || saving.value) return

  saving.value = true
  settingsError.value = ''

  try {
    const payload = await callTypedBridge('saveSettings', toBridgeSettings(draftSettings.value))
    const normalized = normalizeSettings(payload)
    savedSettings.value = cloneSettings(normalized)
    draftSettings.value = cloneSettings(normalized)
    flashOperationMessage('设置已保存')
  } catch (error) {
    showSettingsError(error)
  } finally {
    saving.value = false
  }
}

function cancelSettingsChanges(): void {
  if (!savedSettings.value || saving.value) return
  draftSettings.value = cloneSettings(savedSettings.value)
  settingsError.value = ''
  flashOperationMessage('已取消未保存修改')
}

async function testModelConnection(): Promise<void> {
  if (!draftSettings.value || testingConnection.value) return

  testingConnection.value = true
  settingsError.value = ''
  await nextTick()

  try {
    const result = await callBridgeJob<{ message?: string }>('test_model_connection', toBridgeSettings(draftSettings.value))
    ElMessage.success(result.message || '模型连接测试通过')
  } catch (error) {
    showSettingsError(error)
  } finally {
    testingConnection.value = false
  }
}

function addSensitiveKeyword(): void {
  const keyword = keywordInput.value.trim()
  if (!keyword || !draftSettings.value) return

  const keywords = draftSettings.value.privacy.sensitive_keywords
  if (!keywords.includes(keyword)) {
    draftSettings.value.privacy.sensitive_keywords = [...keywords, keyword]
  }
  keywordInput.value = ''
}

function removeSensitiveKeyword(keyword: string): void {
  if (!draftSettings.value) return
  draftSettings.value.privacy.sensitive_keywords = draftSettings.value.privacy.sensitive_keywords.filter(
    (item) => item !== keyword
  )
}

async function selectYasbStatusDirectory(): Promise<void> {
  if (!draftSettings.value) return

  const currentDirectory = directoryFromPath(draftSettings.value.yasb.status_json_path)
  const result = await callBridge<{ path?: string }>('select_directory', {
    title: '选择 YASB 状态文件存放目录',
    currentPath: currentDirectory
  })
  if (!result.path) return

  draftSettings.value.yasb.status_json_path = joinPath(result.path, 'status.json')
}

async function selectSettingsJsonFile(): Promise<void> {
  if (!draftSettings.value) return

  const result = await callBridge<{ path?: string }>('select_json_file', {
    title: '选择配置 JSON 保存位置',
    currentPath: draftSettings.value.settings_path || '',
    defaultFileName: 'local_settings.json'
  })
  if (!result.path) return

  draftSettings.value.settings_path = result.path
}

function flashOperationMessage(message: string): void {
  operationMessage.value = message
  window.setTimeout(() => {
    if (operationMessage.value === message) {
      operationMessage.value = ''
    }
  }, 2600)
}

function showSettingsError(error: unknown): void {
  const message = error instanceof Error ? error.message : String(error)
  settingsError.value = message
  ElMessage.error(message)
}

function normalizeSettings(payload: LocalSettingsPayload): SettingsDraft {
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

function cloneSettings(settings: SettingsDraft): SettingsDraft {
  return JSON.parse(JSON.stringify(settings)) as SettingsDraft
}

function toBridgeSettings(settings: SettingsDraft): LocalSettingsPayload {
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

function stableSettingsJson(settings: SettingsDraft): string {
  return JSON.stringify(toBridgeSettings(settings))
}

function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  const number = Number(value)
  if (!Number.isFinite(number)) return fallback
  return Math.min(max, Math.max(min, number))
}

function normalizeLoggingLevel(value: unknown): LoggingLevel {
  const level = String(value || 'INFO').toUpperCase()
  return ['DEBUG', 'INFO', 'WARNING', 'ERROR'].includes(level) ? (level as LoggingLevel) : 'INFO'
}

function directoryFromPath(path: string | undefined): string {
  const value = path?.trim()
  if (!value) return ''
  const slashIndex = Math.max(value.lastIndexOf('/'), value.lastIndexOf('\\'))
  return slashIndex > 0 ? value.slice(0, slashIndex) : value
}

function joinPath(directory: string, fileName: string): string {
  const trimmed = directory.trim()
  if (!trimmed) return fileName
  const separator = trimmed.includes('\\') ? '\\' : '/'
  return trimmed.endsWith('/') || trimmed.endsWith('\\') ? `${trimmed}${fileName}` : `${trimmed}${separator}${fileName}`
}

watch(
  [topBarSaveStatus, hasUnsavedChanges, saving, loading],
  ([status]) => {
    appStore.setTopBarState({
      mode: 'app-config',
      statusText: status.text,
      statusTone: status.tone,
      canCancel: hasUnsavedChanges.value && !saving.value,
      canRefresh: !saving.value,
      canSave: hasUnsavedChanges.value && !saving.value,
      refreshing: loading.value,
      saving: saving.value
    })
  },
  { immediate: true }
)

watch(
  () => appStore.topBar.saveRequestId,
  () => {
    if (appStore.topBar.mode !== 'app-config') return
    void saveSettings()
  }
)

watch(
  () => appStore.topBar.cancelRequestId,
  () => {
    if (appStore.topBar.mode !== 'app-config') return
    cancelSettingsChanges()
  }
)

watch(
  () => appStore.topBar.refreshRequestId,
  () => {
    if (appStore.topBar.mode !== 'app-config') return
    void loadSettings()
  }
)

onMounted(() => {
  void loadSettings()
})

onBeforeUnmount(() => {
  appStore.resetTopBarState()
})
</script>

<template>
  <div class="settings-root">
    <div v-if="loading && !draftSettings" class="settings-loading">
      <el-icon class="settings-loading-icon"><Refresh /></el-icon>
      <span>正在读取本地配置...</span>
    </div>

    <div v-else-if="draftSettings" class="settings-scroll">
      <div class="settings-tab-panel">
        <el-tabs type="card" v-model="activeSettingsTab" class="settings-tabs">
          <el-tab-pane label="采集设置" name="collector">
            <SettingsSection
              title="采集设置"
              description="控制桌面活动、剪贴板、浏览器历史和 AI Prompt 进入素材池的方式。"
              :icon="DataAnalysis"
            >
              <div class="collector-toggle-grid">
                <button
                  v-for="collector in collectorCards"
                  :key="collector.key"
                  class="collector-toggle-card"
                  :class="{ 'collector-toggle-card--active': collector.enabled }"
                  type="button"
                  @click="collector.update(!collector.enabled)"
                >
                  <span class="collector-toggle-title">{{ collector.title }}</span>
                  <span class="collector-toggle-description">{{ collector.description }}</span>
                  <el-switch :model-value="collector.enabled" @change="collector.update(Boolean($event))" @click.stop />
                </button>
              </div>

              <SettingsField label="前台应用轮询间隔" description="数值越小响应越及时，也会更频繁访问窗口信息。">
                <div class="settings-inline-control">
                  <el-slider
                    v-model="draftSettings.collector.foreground_poll_interval_sec"
                    :min="1"
                    :max="60"
                    :step="1"
                  />
                  <span class="settings-value">{{ draftSettings.collector.foreground_poll_interval_sec }} 秒</span>
                </div>
              </SettingsField>

              <SettingsField label="Edge 同步间隔" description="浏览器历史同步的最小间隔，适合按分钟级别拉取新访问记录。">
                <div class="settings-inline-control">
                  <el-slider
                    v-model="draftSettings.collector.edge_sync_interval_min"
                    :min="1"
                    :max="120"
                    :step="1"
                  />
                  <span class="settings-value">{{ draftSettings.collector.edge_sync_interval_min }} 分钟</span>
                </div>
              </SettingsField>
            </SettingsSection>
          </el-tab-pane>

          <el-tab-pane label="隐私规则" name="privacy">
            <SettingsSection
              title="隐私规则"
              description="设置敏感内容的默认处理方式，降低日报生成前泄露私密信息的风险。"
              :icon="Lock"
            >
              <SettingsField label="默认隐藏敏感项" description="进入素材列表时先折叠或隐藏命中的敏感内容。" compact>
                <el-switch v-model="draftSettings.privacy.hide_sensitive_by_default" />
              </SettingsField>

              <SettingsField label="敏感项默认不选中" description="生成日报前需要手动勾选敏感素材。" compact>
                <el-switch v-model="draftSettings.privacy.sensitive_unselected_by_default" />
              </SettingsField>

              <SettingsField label="调用模型前人工确认" description="把 Prompt 交给模型前保留一次显式确认。" compact>
                <el-switch v-model="draftSettings.privacy.require_manual_confirm_before_llm" />
              </SettingsField>

              <SettingsField label="剪贴板仅保留预览" description="只展示摘要预览，避免完整剪贴板内容在界面上过度暴露。" compact>
                <el-switch v-model="draftSettings.privacy.clipboard_preview_only" />
              </SettingsField>

              <SettingsField label="敏感关键词" description="命中这些关键词的素材会按敏感内容处理，可按需增删。" wide>
                <div class="keyword-editor">
                  <div class="keyword-tags" aria-label="敏感关键词列表">
                    <el-tag
                      v-for="keyword in draftSettings.privacy.sensitive_keywords"
                      :key="keyword"
                      closable
                      :disable-transitions="true"
                      @close="removeSensitiveKeyword(keyword)"
                    >
                      {{ keyword }}
                    </el-tag>
                    <span v-if="draftSettings.privacy.sensitive_keywords.length === 0" class="keyword-empty">
                      暂无敏感关键词
                    </span>
                  </div>
                  <div class="keyword-add-row">
                    <el-input
                      v-model="keywordInput"
                      placeholder="输入关键词"
                      clearable
                      @keyup.enter="addSensitiveKeyword"
                    />
                    <el-button :icon="Plus" :disabled="!keywordInput.trim()" @click="addSensitiveKeyword">
                      添加
                    </el-button>
                  </div>
                </div>
              </SettingsField>
            </SettingsSection>
          </el-tab-pane>

          <el-tab-pane label="模型设置" name="model">
            <SettingsSection
              title="模型设置"
              description="配置日报生成使用的模型服务。"
              :icon="Cpu"
            >
              <template #actions>
                <el-button
                  type="primary"
                  :icon="Connection"
                  :loading="testingConnection"
                  :disabled="!draftSettings"
                  @click="testModelConnection"
                >
                  测试模型
                </el-button>
              </template>

              <SettingsField label="模型供应商" description="当前后端按 OpenAI 兼容接口调用，默认使用 DeepSeek。">
                <el-select v-model="draftSettings.model.provider">
                  <el-option label="DeepSeek" value="deepseek" />
                  <el-option label="OpenAI 兼容" value="openai-compatible" />
                  <el-option label="自定义" value="custom" />
                </el-select>
              </SettingsField>

              <SettingsField label="模型名称" description="例如 deepseek-chat、deepseek-reasoner 或兼容接口中的模型 ID。">
                <el-input v-model="draftSettings.model.model_name" placeholder="deepseek-chat" />
              </SettingsField>

              <SettingsField label="接口地址" description="OpenAI 兼容接口的 base URL。">
                <el-input v-model="draftSettings.model.base_url" placeholder="https://api.deepseek.com" />
              </SettingsField>

              <SettingsField label="API Key" description="留空时后端会继续按环境变量优先级读取密钥。">
                <el-input
                  v-model="draftSettings.model.api_key"
                  type="password"
                  show-password
                  placeholder="从环境变量或本地设置读取"
                />
              </SettingsField>

              <SettingsField label="Prompt 最大字符数" description="限制发送给模型的素材规模，避免上下文过长。">
                <el-input-number
                  v-model="draftSettings.model.max_prompt_chars"
                  :min="1000"
                  :max="200000"
                  :step="1000"
                  controls-position="right"
                />
              </SettingsField>

              <SettingsField label="请求超时" description="模型请求最长等待时间。">
                <el-input-number
                  v-model="draftSettings.model.timeout_seconds"
                  :min="5"
                  :max="300"
                  :step="5"
                  controls-position="right"
                />
              </SettingsField>

              <SettingsField label="生成温度" description="较低更稳定，较高更发散。日报建议保持在 0.2 到 0.5。">
                <div class="settings-inline-control">
                  <el-slider v-model="draftSettings.model.temperature" :min="0" :max="2" :step="0.1" />
                  <span class="settings-value">{{ draftSettings.model.temperature.toFixed(1) }}</span>
                </div>
              </SettingsField>
            </SettingsSection>
          </el-tab-pane>

          <el-tab-pane label="系统集成" name="system">
            <SettingsSection
              title="系统集成"
              description="维护状态栏联动、日志保留和配置文件位置。"
              :icon="Monitor"
            >
              <SettingsField label="YASB 状态命令" description="状态栏组件可通过该命令读取采集器状态。">
                <el-input v-model="draftSettings.yasb.status_cli_command" placeholder="daily-report status --json" />
              </SettingsField>

              <SettingsField label="YASB 状态 JSON" description="文件名固定为 status.json，只需要选择状态文件存放目录。" wide>
                <el-input
                  :model-value="draftSettings.yasb.status_json_path"
                  readonly
                  placeholder="默认状态文件路径"
                >
                  <template #append>
                    <el-button
                      :icon="FolderOpened"
                      title="选择状态文件存放目录"
                      aria-label="选择状态文件存放目录"
                      @click="selectYasbStatusDirectory"
                    />
                  </template>
                </el-input>
              </SettingsField>

              <SettingsField label="日志等级" description="DEBUG 会输出更多诊断信息，日常建议使用 INFO。">
                <el-select v-model="draftSettings.logging.level">
                  <el-option label="DEBUG" value="DEBUG" />
                  <el-option label="INFO" value="INFO" />
                  <el-option label="WARNING" value="WARNING" />
                  <el-option label="ERROR" value="ERROR" />
                </el-select>
              </SettingsField>

              <SettingsField label="日志保留天数" description="后续清理任务可按这个窗口保留运行日志。">
                <el-input-number
                  v-model="draftSettings.logging.retention_days"
                  :min="1"
                  :max="3650"
                  :step="1"
                  controls-position="right"
                />
              </SettingsField>

              <SettingsField label="配置文件" description="选择本地 JSON 配置文件保存位置，便于离线使用和手动备份。" wide>
                <el-input
                  :model-value="draftSettings.settings_path"
                  readonly
                  placeholder="浏览器预览模式"
                >
                  <template #append>
                    <el-button
                      :icon="FolderOpened"
                      title="选择配置 JSON 保存位置"
                      aria-label="选择配置 JSON 保存位置"
                      @click="selectSettingsJsonFile"
                    />
                  </template>
                </el-input>
              </SettingsField>
            </SettingsSection>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-root {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  overflow: hidden;
}

.settings-loading {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #667085;
  font-size: 14px;
}

.settings-loading-icon {
  animation: settings-spin 900ms linear infinite;
}

.settings-scroll {
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.settings-tab-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 16px 16px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.settings-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.settings-tabs :deep(.el-tabs__header) {
  margin: 0 0 14px;
  padding: 0 2px;
}

.settings-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.settings-tabs :deep(.el-tab-pane) {
  min-height: 0;
  height: 100%;
}

.collector-toggle-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 18px 20px;
  border-bottom: 1px solid #edf1f7;
}

.collector-toggle-card {
  min-width: 0;
  min-height: 116px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 8px;
  padding: 14px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #526179;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    box-shadow 160ms ease;
}

.collector-toggle-card:hover {
  border-color: #bfdbfe;
  background: #f8fbff;
}

.collector-toggle-card--active {
  border-color: #bfdbfe;
  background: #eff6ff;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.collector-toggle-title {
  color: #172033;
  font-size: 13px;
  font-weight: 780;
  line-height: 1.3;
}

.collector-toggle-description {
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.collector-toggle-card :deep(.el-switch) {
  justify-self: end;
}

.settings-inline-control {
  min-width: 0;
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 58px;
  gap: 12px;
  align-items: center;
}

.settings-value {
  color: #526179;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  text-align: right;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.keyword-editor {
  width: 100%;
  display: grid;
  gap: 10px;
}

.keyword-tags {
  min-height: 76px;
  display: flex;
  align-content: flex-start;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #f8fafc;
}

.keyword-empty {
  color: #98a2b3;
  font-size: 12px;
  line-height: 24px;
}

.keyword-add-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}

@keyframes settings-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .collector-toggle-grid {
    grid-template-columns: minmax(0, 1fr);
    padding: 16px;
  }

  .keyword-add-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
