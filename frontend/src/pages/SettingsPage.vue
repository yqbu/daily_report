<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-3xl font-black tracking-tight">设置</h2>
      <p class="mt-2 text-slate-500">当前页面先完成 Web UI 形态，保存类操作后续再逐步接入。</p>
    </div>

    <div class="grid grid-cols-[1fr_1fr] gap-5">
      <section class="card p-5">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="section-title">采集器状态</h3>
            <p class="mt-1 text-sm text-slate-500">来自 Python 后端状态接口</p>
          </div>
          <StatusBadge label="本地服务" tone="green" />
        </div>
        <pre class="max-h-72 overflow-auto rounded-2xl bg-slate-50 p-4 text-sm leading-7 text-slate-700">{{ JSON.stringify(status, null, 2) }}</pre>
      </section>

      <section class="card p-5">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="section-title">模型配置</h3>
            <p class="mt-1 text-sm text-slate-500">读取本地 settings，暂不在 Web UI 内保存。</p>
          </div>
          <StatusBadge label="只读预览" tone="gray" />
        </div>
        <div class="space-y-3">
          <Field label="模型提供商" :value="settings?.model?.provider" />
          <Field label="Base URL" :value="settings?.model?.base_url" />
          <Field label="模型名称" :value="settings?.model?.model_name" />
          <Field label="API Key" :value="settings?.model?.api_key || '未保存'" />
          <Field label="Temperature" :value="settings?.model?.temperature" />
        </div>
      </section>

      <section class="card p-5">
        <h3 class="section-title">隐私与敏感内容</h3>
        <div class="mt-5 grid grid-cols-2 gap-3">
          <div class="info-tile">默认隐藏敏感内容<span>{{ settings?.privacy?.hide_sensitive_by_default ? '开启' : '关闭' }}</span></div>
          <div class="info-tile">敏感内容不入日报<span>{{ settings?.privacy?.sensitive_unselected_by_default ? '开启' : '关闭' }}</span></div>
          <div class="info-tile">调用模型前确认<span>{{ settings?.privacy?.require_manual_confirm_before_llm ? '开启' : '关闭' }}</span></div>
          <div class="info-tile">剪贴板仅保存预览<span>{{ settings?.privacy?.clipboard_preview_only ? '开启' : '关闭' }}</span></div>
        </div>
      </section>

      <section class="card p-5">
        <h3 class="section-title">YASB 与后续接入</h3>
        <p class="mt-4 leading-7 text-slate-600">
          旧的 YASB、collector、storage、report、service 模块保持不变。Web UI 会通过 Bridge 逐步接入已有接口；
          尚未实现的保存、测试连接、详情抽屉联动等功能先用占位 UI 表达状态。
        </p>
        <div class="mt-5 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm font-semibold text-blue-700">
          Web 前端只负责展示和交互，所有本地数据读取仍由 Python 完成。
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h, onMounted, ref } from 'vue'
import { callBridge } from '../api/bridge'
import StatusBadge from '../components/StatusBadge.vue'

const settings = ref<Record<string, any> | null>(null)
const status = ref<Record<string, unknown> | null>(null)

const Field = defineComponent({
  props: { label: String, value: [String, Number, Boolean] },
  setup(props) {
    return () => h('div', { class: 'flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3' }, [
      h('span', { class: 'text-sm font-semibold text-slate-500' }, props.label),
      h('span', { class: 'max-w-[360px] truncate text-sm font-bold text-slate-800' }, String(props.value ?? '-'))
    ])
  }
})

onMounted(async () => {
  settings.value = await callBridge<Record<string, any>>('get_settings')
  status.value = await callBridge<Record<string, unknown>>('get_collector_status')
})
</script>

<style scoped>
.info-tile {
  min-height: 92px;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  padding: 18px;
  color: #475569;
  font-weight: 800;
}

.info-tile span {
  margin-top: 10px;
  display: block;
  color: #2563eb;
  font-size: 24px;
  font-weight: 900;
}
</style>
