<script setup lang="ts">
import { onMounted, reactive, shallowRef } from 'vue'

import { callTypedBridge } from '../api/bridge'
import type { HealthPayload, LocalSettingsPayload } from '../api/types'
import PageLayout from '../layouts/PageLayout.vue'

/**
 * 设置页骨架。
 *
 * 页面职责：
 * - 读取本地配置：getSettings
 * - 保存本地配置：saveSettings
 * - 查看运行健康状态：getHealth
 *
 * 布局实现建议：
 * - 顶部或固定底部：保存设置按钮
 * - 分区：采集设置、隐私规则、模型设置、YASB 联动、系统信息
 */

const loading = shallowRef(false)
const saving = shallowRef(false)
const lastError = shallowRef('')
const health = shallowRef<HealthPayload>({})

const settings = reactive<LocalSettingsPayload>({
  model: {
    provider: 'deepseek',
    model_name: 'deepseek-chat',
    base_url: 'https://api.deepseek.com',
    api_key: '',
    max_prompt_chars: 12000,
    timeout_seconds: 60,
    temperature: 0.3
  },
  collector: {
    foreground_enabled: true,
    clipboard_enabled: true,
    edge_history_enabled: true,
    ai_prompt_enabled: true,
    foreground_poll_interval_sec: 2,
    edge_sync_interval_min: 3
  },
  privacy: {
    hide_sensitive_by_default: true,
    sensitive_unselected_by_default: true,
    require_manual_confirm_before_llm: true,
    clipboard_preview_only: true,
    sensitive_keywords: []
  },
  yasb: {
    status_cli_command: 'daily-report status --json',
    status_json_path: ''
  },
  logging: {
    level: 'INFO',
    retention_days: 30
  }
})

async function loadSettings(): Promise<void> {
  loading.value = true
  lastError.value = ''

  try {
    const [settingsPayload, healthPayload] = await Promise.all([
      callTypedBridge('getSettings', {}),
      callTypedBridge('getHealth', {})
    ])
    applySettings(settingsPayload)
    health.value = healthPayload
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function saveSettings(): Promise<LocalSettingsPayload | null> {
  saving.value = true
  lastError.value = ''

  try {
    const saved = await callTypedBridge('saveSettings', settings)
    applySettings(saved)
    return saved
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
    return null
  } finally {
    saving.value = false
  }
}

function applySettings(payload: Partial<LocalSettingsPayload>): void {
  if (payload.model) Object.assign(settings.model, payload.model)
  if (payload.collector) Object.assign(settings.collector, payload.collector)
  if (payload.privacy) Object.assign(settings.privacy, payload.privacy)
  if (payload.logging) Object.assign(settings.logging, payload.logging)
  if (payload.yasb) settings.yasb = { ...(settings.yasb || {}), ...payload.yasb }
  settings.settings_path = payload.settings_path || payload.settingsPath || settings.settings_path
}

onMounted(loadSettings)

defineExpose({
  loading,
  saving,
  lastError,
  settings,
  health,
  loadSettings,
  saveSettings,
  applySettings
})
</script>

<template>
  <PageLayout title="设置" scrollable>
    <section class="page-skeleton" v-loading="loading">
      <!--
        数据状态：
        - settings: LocalSettingsPayload
        - health: HealthPayload
        - lastError: string

        后端接口：
        - getSettings() -> LocalSettingsPayload
        - saveSettings(settings) -> LocalSettingsPayload
        - getHealth() -> HealthPayload

        待实现页面区域：
        1. 采集设置
        2. 隐私规则
        3. 模型设置
        4. YASB 联动
        5. 系统信息
        6. 全局保存操作区，避免放进单个设置卡片
      -->
    </section>
  </PageLayout>
</template>

<style scoped>
.page-skeleton {
  min-height: 100%;
}
</style>
