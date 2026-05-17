<template>
  <PageLayout title="设置" subtitle="配置模型、采集、隐私和界面行为">
    <template #actions>
      <el-button class="glass-button" :icon="Files">本地配置</el-button>
      <el-button class="glass-button" :icon="Lock">安全存储</el-button>
      <el-button class="glass-button" :icon="Connection">即时测试</el-button>
    </template>

    <div v-loading="loading" class="h-full min-h-0 overflow-auto pr-2">
      <div class="grid min-w-0 grid-cols-2 gap-5 pb-2">
        <div class="min-w-0 space-y-5">
          <section class="app-card p-5">
            <div class="mb-4 flex items-center gap-3">
              <el-icon class="text-blue-600" :size="22"><Files /></el-icon>
              <div>
                <h3 class="section-title">本地配置</h3>
                <p class="mt-1 text-sm text-slate-500">配置文件用于保存应用设置与采集规则。</p>
              </div>
            </div>
            <div class="grid grid-cols-[1fr_auto_auto] gap-3">
              <el-input v-model="form.settingsPath" readonly />
              <el-button class="glass-button" :icon="FolderOpened">选择文件</el-button>
              <el-button class="glass-button" :icon="Folder">打开目录</el-button>
            </div>
          </section>

          <section class="app-card p-5">
            <h3 class="section-title mb-4">采集设置</h3>
            <div class="space-y-4">
              <SettingSwitch v-model="form.collector.foreground_enabled" label="启用前台窗口采集" />
              <SettingSwitch v-model="form.collector.clipboard_enabled" label="启用剪贴板采集" />
              <SettingSwitch v-model="form.collector.edge_history_enabled" label="启用浏览记录采集" />
              <SettingSwitch v-model="form.collector.ai_prompt_enabled" label="启用 AI 提问采集" />
              <div class="grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
                <Field label="前台轮询间隔（秒）"><el-input-number v-model="form.collector.foreground_poll_interval_sec" :min="1" :max="60" class="w-full" /></Field>
                <Field label="Edge 同步间隔（分钟）"><el-input-number v-model="form.collector.edge_sync_interval_min" :min="1" :max="120" class="w-full" /></Field>
              </div>
            </div>
          </section>

          <section class="app-card p-5">
            <h3 class="section-title mb-4">隐私与敏感内容</h3>
            <div class="space-y-4">
              <SettingSwitch v-model="form.privacy.hide_sensitive_by_default" label="默认隐藏敏感内容" />
              <SettingSwitch v-model="form.privacy.sensitive_unselected_by_default" label="敏感内容默认不入日报" />
              <SettingSwitch v-model="form.privacy.require_manual_confirm_before_llm" label="调用模型前需人工确认" />
              <SettingSwitch v-model="form.privacy.clipboard_preview_only" label="剪贴板仅保存预览" />
              <div class="rounded-2xl border border-slate-100 bg-slate-50 p-3">
                <div class="mb-2 text-sm font-bold text-slate-600">敏感关键词</div>
                <div class="flex flex-wrap gap-2">
                  <el-tag v-for="keyword in form.privacy.sensitive_keywords" :key="keyword" closable effect="light" round>{{ keyword }}</el-tag>
                  <el-button class="glass-button" size="small" :icon="Plus">添加</el-button>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div class="min-w-0 space-y-5">
          <section class="app-card p-5">
            <h3 class="section-title mb-4">模型设置</h3>
            <el-form label-position="top" class="settings-form">
              <div class="grid grid-cols-2 gap-4">
                <el-form-item label="模型提供商"><el-input v-model="form.model.provider" /></el-form-item>
                <el-form-item label="模型名称"><el-input v-model="form.model.model_name" /></el-form-item>
              </div>
              <el-form-item label="Base URL"><el-input v-model="form.model.base_url" /></el-form-item>
              <el-form-item label="API Key"><el-input v-model="form.model.api_key" type="password" show-password /></el-form-item>
              <div class="grid grid-cols-3 gap-4">
                <el-form-item label="最大 Prompt 长度"><el-input-number v-model="form.model.max_prompt_chars" :min="1000" :max="200000" :step="1000" class="w-full" /></el-form-item>
                <el-form-item label="Temperature"><el-input-number v-model="form.model.temperature" :min="0" :max="2" :step="0.1" :precision="2" class="w-full" /></el-form-item>
                <el-form-item label="请求超时（秒）"><el-input-number v-model="form.model.timeout_seconds" :min="5" :max="300" :step="5" class="w-full" /></el-form-item>
              </div>
              <div class="mt-2 grid grid-cols-2 gap-3">
                <el-button class="glass-button" :icon="Connection" @click="notImplemented('测试模型连接')">测试模型连接</el-button>
                <el-button class="primary-gradient" :icon="DocumentChecked" @click="notImplemented('保存设置')">保存设置</el-button>
              </div>
            </el-form>
          </section>

          <section class="app-card p-5">
            <h3 class="section-title mb-4">日志与保留</h3>
            <div class="grid grid-cols-2 gap-4">
              <Field label="日志级别">
                <el-select v-model="form.logging.level" class="w-full">
                  <el-option label="DEBUG" value="DEBUG" />
                  <el-option label="INFO" value="INFO" />
                  <el-option label="WARNING" value="WARNING" />
                  <el-option label="ERROR" value="ERROR" />
                </el-select>
              </Field>
              <Field label="日志保留天数"><el-input-number v-model="form.logging.retention_days" :min="1" :max="3650" class="w-full" /></Field>
            </div>
          </section>

          <section class="app-card p-5">
            <div class="mb-4 flex items-center justify-between">
              <h3 class="section-title">采集器状态</h3>
              <el-tag :type="collectorTone" effect="light" round>{{ collectorLabel }}</el-tag>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <InfoTile label="今日活跃" :value="String(status?.active_time || '-')" />
              <InfoTile label="记录数" :value="String(status?.session_count || 0)" />
              <InfoTile label="进程数" :value="String(status?.collector_process_count || 0)" />
            </div>
            <el-collapse class="mt-4">
              <el-collapse-item title="原始状态 JSON" name="raw">
                <pre class="scroll-pre max-h-52 rounded-2xl bg-slate-50 p-4 text-xs leading-6">{{ JSON.stringify(status, null, 2) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </section>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref, resolveComponent } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, DocumentChecked, Files, Folder, FolderOpened, Lock, Plus } from '@element-plus/icons-vue'
import { callBridge } from '../api/bridge'
import PageLayout from '../layouts/PageLayout.vue'

const loading = ref(false)
const status = ref<Record<string, any> | null>(null)
const form = reactive({
  settingsPath: 'data/local_settings.json',
  model: { provider: 'deepseek', model_name: 'deepseek-chat', base_url: 'https://api.deepseek.com', api_key: '', max_prompt_chars: 12000, timeout_seconds: 60, temperature: 0.3 },
  collector: { foreground_enabled: true, clipboard_enabled: true, edge_history_enabled: true, ai_prompt_enabled: true, foreground_poll_interval_sec: 2, edge_sync_interval_min: 3 },
  privacy: { hide_sensitive_by_default: true, sensitive_unselected_by_default: true, require_manual_confirm_before_llm: true, clipboard_preview_only: true, sensitive_keywords: [] as string[] },
  logging: { level: 'INFO', retention_days: 30 }
})
const collectorLabel = computed(() => String(status.value?.collector_status_label || '未知'))
const collectorTone = computed(() => status.value?.collector_status === 'running' ? 'success' : 'warning')

const Field = defineComponent({
  props: { label: String },
  setup(props, { slots }) {
    return () => h('div', { class: 'min-w-0' }, [
      h('div', { class: 'mb-2 text-sm font-bold text-slate-600' }, props.label),
      slots.default?.()
    ])
  }
})

const SettingSwitch = defineComponent({
  props: { modelValue: Boolean, label: String },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const ElSwitch = resolveComponent('el-switch')
    return () => h('div', { class: 'flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3' }, [
      h('span', { class: 'text-sm font-bold text-slate-700' }, props.label),
      h(ElSwitch, {
        modelValue: props.modelValue,
        'onUpdate:modelValue': (value: boolean) => emit('update:modelValue', value)
      })
    ])
  }
})

const InfoTile = defineComponent({
  props: { label: String, value: String },
  setup(props) {
    return () => h('div', { class: 'rounded-2xl border border-slate-100 bg-slate-50 p-4' }, [
      h('div', { class: 'text-xs font-bold text-slate-500' }, props.label),
      h('div', { class: 'mt-2 truncate text-2xl font-black text-slate-900' }, props.value)
    ])
  }
})

async function load() {
  loading.value = true
  try {
    const settings = await callBridge<Record<string, any>>('get_settings')
    status.value = await callBridge<Record<string, any>>('get_collector_status')
    Object.assign(form.model, settings.model || {})
    Object.assign(form.collector, settings.collector || {})
    Object.assign(form.privacy, settings.privacy || {})
    Object.assign(form.logging, settings.logging || {})
  } finally {
    loading.value = false
  }
}

function notImplemented(action: string) {
  ElMessage.info(`${action}的后端保存逻辑后续接入，当前先保留界面。`)
}

onMounted(load)
</script>

<style scoped>
.settings-form :deep(.el-form-item) {
  margin-bottom: 16px;
}
</style>
