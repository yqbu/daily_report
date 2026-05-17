<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-black tracking-tight">日报工作台</h2>
        <p class="mt-2 text-slate-500">筛选素材、预览 Prompt，并生成 Markdown 日报。</p>
      </div>
      <DateRangeFilter v-model="app.currentDate" @refresh="refresh" />
    </div>

    <div class="grid grid-cols-[360px_1fr_430px] gap-5">
      <section class="card min-h-[680px] p-5">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="section-title">已选素材</h3>
            <p class="mt-1 text-sm text-slate-500">{{ report.selectedTotal }} / {{ report.materialTotal }} 条</p>
          </div>
          <StatusBadge label="实时保存" tone="green" />
        </div>
        <div v-if="report.materials.length" class="max-h-[590px] space-y-2 overflow-y-auto pr-1">
          <label v-for="item in report.materials" :key="item.key" class="block rounded-2xl border border-slate-200 bg-white p-3 transition hover:border-blue-200 hover:bg-blue-50/40">
            <div class="flex items-start gap-3">
              <input class="mt-1 h-4 w-4 accent-blue-600" type="checkbox" :checked="item.selected" @change="toggle(item.key, ($event.target as HTMLInputElement).checked)" />
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-slate-500">{{ item.time }}</span>
                  <StatusBadge :label="item.source_type" :tone="item.sensitive ? 'red' : 'blue'" />
                </div>
                <p class="mt-2 line-clamp-2 text-sm font-semibold text-slate-800">{{ item.preview || item.source }}</p>
                <p class="mt-1 truncate text-xs text-slate-500">{{ item.source }}</p>
              </div>
            </div>
          </label>
        </div>
        <EmptyState v-else title="暂无可用素材" description="运行采集服务后，素材会自动出现在这里。" />
      </section>

      <section class="space-y-5">
        <ChartCard title="素材摘要" subtitle="由 Python 后端基于已选素材构建">
          <pre class="min-h-64 whitespace-pre-wrap rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-7 text-slate-700">{{ report.prompt || '点击刷新后生成 Prompt 预览。' }}</pre>
          <div class="mt-4 flex justify-end">
            <button class="secondary-button" @click="report.buildPrompt(app.currentDate)">刷新 Prompt</button>
          </div>
        </ChartCard>

        <ChartCard title="生成选项">
          <div class="grid grid-cols-3 gap-3">
            <div class="option-card">
              <div class="font-bold">保存版本</div>
              <p>生成后写入日报历史</p>
            </div>
            <div class="option-card muted-option">
              <div class="font-bold">敏感确认</div>
              <p>沿用本地隐私设置</p>
            </div>
            <div class="option-card muted-option">
              <div class="font-bold">模板策略</div>
              <p>后续接入自定义模板</p>
            </div>
          </div>
        </ChartCard>
      </section>

      <section class="card flex min-h-[680px] flex-col p-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="section-title">日报输出</h3>
          <StatusBadge :label="report.generating ? '生成中' : '待生成'" :tone="report.generating ? 'orange' : 'gray'" />
        </div>
        <pre class="min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-7 text-slate-800">{{ report.generatedMarkdown || placeholderMarkdown }}</pre>
        <p v-if="report.error" class="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-600">{{ report.error }}</p>
        <div class="mt-4 grid grid-cols-2 gap-3">
          <button class="primary-button" :disabled="report.generating" @click="report.generate(app.currentDate)">
            {{ report.generating ? '生成中...' : '生成日报' }}
          </button>
          <button class="secondary-button" :disabled="!report.generatedMarkdown" @click="copyMarkdown">复制 Markdown</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ChartCard from '../components/ChartCard.vue'
import DateRangeFilter from '../components/DateRangeFilter.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAppStore } from '../stores/app'
import { useReportStore } from '../stores/report'

const app = useAppStore()
const report = useReportStore()
const placeholderMarkdown = '# 日报预览\n\n当前还没有生成内容。确认素材后点击“生成日报”，结果会显示在这里。'

async function refresh() {
  await report.loadMaterials(app.currentDate)
  await report.buildPrompt(app.currentDate)
}

function toggle(key: string, selected: boolean) {
  report.updateSelected(key, selected)
}

function copyMarkdown() {
  navigator.clipboard?.writeText(report.generatedMarkdown)
}

onMounted(refresh)
</script>

<style scoped>
.primary-button,
.secondary-button {
  height: 44px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 800;
}

.primary-button {
  background: #2563eb;
  color: white;
}

.primary-button:disabled {
  opacity: .6;
}

.secondary-button {
  border: 1px solid #dbe3ef;
  background: white;
  color: #475569;
}

.secondary-button:disabled {
  cursor: not-allowed;
  opacity: .45;
}

.option-card {
  border-radius: 16px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  padding: 16px;
  color: #1d4ed8;
}

.option-card p {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.muted-option {
  border-color: #e2e8f0;
  background: #f8fafc;
  color: #475569;
}
</style>
