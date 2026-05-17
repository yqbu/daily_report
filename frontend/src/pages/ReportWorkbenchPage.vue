<template>
  <PageLayout title="日报工作台" subtitle="筛选素材、生成日报并查看历史版本的一体化工作流">
    <template #actions>
      <el-button class="glass-button" :icon="Filter">范围筛选</el-button>
      <el-button class="glass-button" :icon="Grid">结构化生成</el-button>
      <el-button class="glass-button" :icon="Clock">版本历史</el-button>
    </template>

    <div class="flex h-full min-h-0 min-w-0 flex-col gap-4 overflow-hidden">
      <el-steps :active="1" align-center class="shrink-0">
        <el-step title="数据筛选" />
        <el-step title="素材确认" />
        <el-step title="生成日报" />
        <el-step title="历史版本" />
      </el-steps>

      <div class="grid min-h-0 min-w-0 flex-1 grid-cols-[330px_minmax(0,1fr)_390px] gap-5">
        <section class="app-card flex min-h-0 min-w-0 flex-col overflow-hidden p-4">
          <div class="mb-3 flex shrink-0 items-center justify-between">
            <div>
              <h3 class="section-title">已选素材</h3>
              <p class="mt-1 text-sm text-slate-500">共 {{ report.materialTotal }} 条，已选 {{ report.selectedTotal }} 条</p>
            </div>
            <el-tag effect="light" round>{{ materialPageText }}</el-tag>
          </div>
          <div class="mb-3 grid shrink-0 grid-cols-[1fr_auto] gap-2">
            <el-date-picker v-model="app.currentDate" type="date" value-format="YYYY-MM-DD" :clearable="false" @change="refresh" />
            <el-button class="glass-button" :icon="Refresh" @click="refresh">刷新</el-button>
          </div>
          <el-input v-model="materialKeyword" :prefix-icon="Search" clearable placeholder="搜索标题、内容或来源..." class="mb-3 shrink-0" />
          <div class="min-h-0 flex-1 overflow-auto pr-1">
            <label v-for="item in visibleMaterials" :key="item.key" class="material-row">
              <el-checkbox :model-value="item.selected" @change="(value: boolean) => toggle(item.key, value)" />
              <div class="min-w-0 flex-1">
                <div class="mb-1 flex min-w-0 items-center gap-2">
                  <span class="shrink-0 text-xs font-bold text-slate-500">{{ item.time }}</span>
                  <el-tag size="small" effect="light" round>{{ item.source_type }}</el-tag>
                  <el-tag v-if="item.sensitive" size="small" type="danger" effect="light" round>敏感</el-tag>
                </div>
                <p class="line-clamp-2 text-sm font-bold leading-5 text-slate-800">{{ item.preview || item.source }}</p>
                <p class="mt-1 truncate text-xs text-slate-500">{{ item.source }}</p>
              </div>
            </label>
            <EmptyState v-if="!visibleMaterials.length" title="暂无可用素材" description="当前筛选条件下没有素材。" />
          </div>
          <AppPagination
            :page="materialPage"
            :page-size="materialPageSize"
            :total="filteredMaterials.length"
            compact
            @size-change="changeMaterialPageSize"
            @current-change="materialPage = $event"
          />
        </section>

        <section class="grid min-h-0 min-w-0 grid-rows-[minmax(0,1fr)_minmax(0,.78fr)] gap-5">
          <ChartCard title="素材摘要" subtitle="基于已选素材构建的生成上下文">
            <template #actions>
              <el-button class="glass-button" :icon="Refresh" @click="report.buildPrompt(app.currentDate)">重新汇总素材</el-button>
            </template>
            <pre class="scroll-pre h-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-7 text-slate-700">{{ report.prompt || '点击“重新汇总素材”生成 Prompt 预览。' }}</pre>
          </ChartCard>
          <ChartCard title="Prompt（可编辑）">
            <template #actions>
              <el-button class="glass-button" :icon="FullScreen">展开</el-button>
            </template>
            <el-input
              v-model="report.prompt"
              type="textarea"
              resize="none"
              class="prompt-editor"
              placeholder="Prompt 内容会显示在这里"
            />
          </ChartCard>
        </section>

        <section class="grid min-h-0 min-w-0 grid-rows-[minmax(0,1fr)_245px] gap-5">
          <ChartCard title="日报输出">
            <template #actions>
              <el-tag :type="report.generating ? 'warning' : 'info'" effect="light" round>{{ report.generating ? '生成中' : '待生成' }}</el-tag>
            </template>
            <div class="flex h-full min-h-0 flex-col overflow-hidden">
              <pre class="scroll-pre min-h-0 flex-1 rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-7 text-slate-800">{{ report.generatedMarkdown || placeholderMarkdown }}</pre>
              <p v-if="report.error" class="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-bold text-red-600">{{ report.error }}</p>
              <div class="mt-3 grid shrink-0 grid-cols-2 gap-3">
                <el-button class="primary-gradient" :loading="report.generating" @click="report.generate(app.currentDate)">生成日报</el-button>
                <el-button class="glass-button" :disabled="!report.generatedMarkdown" @click="copyMarkdown">复制 Markdown</el-button>
              </div>
            </div>
          </ChartCard>
          <ChartCard title="历史日报">
            <AppDataTable
              :rows="historyRows"
              :columns="historyColumns"
              :loading="historyLoading"
              height="100%"
              empty-text="暂无历史日报"
              @row-click="previewHistory"
            />
          </ChartCard>
        </section>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Clock, Filter, FullScreen, Grid, Refresh, Search } from '@element-plus/icons-vue'
import { callBridge } from '../api/bridge'
import type { AnyRecord, MaterialRow, PageResult } from '../api/types'
import AppDataTable from '../components/AppDataTable.vue'
import AppPagination from '../components/AppPagination.vue'
import ChartCard from '../components/ChartCard.vue'
import EmptyState from '../components/EmptyState.vue'
import PageLayout from '../layouts/PageLayout.vue'
import { useAppStore } from '../stores/app'
import { useReportStore } from '../stores/report'

const app = useAppStore()
const report = useReportStore()
const materialKeyword = ref('')
const materialPage = ref(1)
const materialPageSize = ref(30)
const historyRows = ref<AnyRecord[]>([])
const historyLoading = ref(false)
const placeholderMarkdown = '# 日报预览\n\n确认素材后点击“生成日报”，Markdown 内容会在这里滚动显示。'
const historyColumns = [
  { key: 'date', label: '日期', minWidth: 96 },
  { key: 'model_name', label: '模型', minWidth: 118 },
  { key: 'created_at', label: '时间', minWidth: 92, formatter: (row: AnyRecord) => timeText(row.created_at) }
]
const filteredMaterials = computed(() => {
  const keyword = materialKeyword.value.trim().toLowerCase()
  if (!keyword) return report.materials
  return report.materials.filter((item) => `${item.preview} ${item.source} ${item.source_type}`.toLowerCase().includes(keyword))
})
const visibleMaterials = computed(() => {
  const start = (materialPage.value - 1) * materialPageSize.value
  return filteredMaterials.value.slice(start, start + materialPageSize.value)
})
const materialPageText = computed(() => `${Math.min(filteredMaterials.value.length, (materialPage.value - 1) * materialPageSize.value + 1)}-${Math.min(filteredMaterials.value.length, materialPage.value * materialPageSize.value)}`)

async function refresh() {
  await report.loadMaterials(app.currentDate)
  await report.buildPrompt(app.currentDate)
  await loadHistory()
}

function toggle(key: string, selected: boolean) {
  report.updateSelected(key, selected)
}

function changeMaterialPageSize(size: number) {
  materialPageSize.value = size
  materialPage.value = 1
}

function copyMarkdown() {
  navigator.clipboard?.writeText(report.generatedMarkdown)
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const data = await callBridge<PageResult<AnyRecord>>('get_report_history', { page: 1, page_size: 8 })
    historyRows.value = data.items
  } finally {
    historyLoading.value = false
  }
}

function previewHistory(row: AnyRecord) {
  report.generatedMarkdown = String(row.report_markdown || '')
  report.prompt = String(row.prompt_text || report.prompt)
}

function timeText(value: unknown) {
  const text = String(value || '')
  return text.length >= 19 ? text.slice(11, 19) : text || '-'
}

onMounted(refresh)
</script>

<style scoped>
.material-row {
  display: flex;
  min-width: 0;
  gap: 10px;
  border: 1px solid #dbe3ef;
  border-radius: 16px;
  background: rgba(255, 255, 255, .84);
  padding: 10px;
  margin-bottom: 8px;
  cursor: pointer;
}

.material-row:hover {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.prompt-editor,
.prompt-editor :deep(.el-textarea__inner) {
  height: 100%;
  min-height: 0;
}
</style>
