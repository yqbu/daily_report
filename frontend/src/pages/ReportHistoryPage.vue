<template>
  <PageLayout title="历史日报" subtitle="查看、检索和复制已经保存的 Markdown 日报">
    <template #actions>
      <el-input v-model="keyword" :prefix-icon="Search" clearable placeholder="搜索模型、Prompt 或日报内容" style="width: 320px" @keyup.enter="loadFirstPage" />
      <el-button class="primary-gradient" :icon="Search" @click="loadFirstPage">搜索</el-button>
    </template>

    <div class="grid h-full min-h-0 min-w-0 grid-cols-[430px_minmax(0,1fr)] gap-5 overflow-hidden">
      <section class="app-card flex min-h-0 min-w-0 flex-col overflow-hidden p-4">
        <div class="mb-3 flex shrink-0 items-center justify-between">
          <div>
            <h3 class="section-title">日报列表</h3>
            <p class="mt-1 text-sm text-slate-500">点击日期查看详情</p>
          </div>
          <el-tag effect="light" round>共 {{ total }} 条</el-tag>
        </div>
        <AppDataTable
          :rows="rows"
          :columns="columns"
          :loading="loading"
          height="100%"
          empty-text="暂无历史日报"
          @row-click="selectReport"
        >
          <template #dateLink="{ row }">
            <span class="font-black text-blue-600">{{ row.date || '-' }}</span>
          </template>
        </AppDataTable>
        <AppPagination
          :page="page"
          :page-size="pageSize"
          :total="total"
          compact
          @size-change="changePageSize"
          @current-change="changePage"
        />
      </section>

      <section class="app-card flex min-h-0 min-w-0 flex-col overflow-hidden p-5">
        <div class="mb-4 flex shrink-0 items-center justify-between gap-3">
          <div class="min-w-0">
            <h3 class="section-title truncate">日报内容</h3>
            <p class="mt-1 truncate text-sm text-slate-500">{{ detail?.model_name || '选择左侧日报查看详情' }}</p>
          </div>
          <el-segmented v-model="activePanel" :options="panelOptions" />
        </div>
        <pre v-if="detail" class="scroll-pre min-h-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-7 text-slate-800">{{ panelText }}</pre>
        <EmptyState v-else title="请选择日报" description="点击左侧列表中的日期，加载日报正文、Prompt 与元数据。" />
      </section>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { callBridge } from '../api/bridge'
import type { AnyRecord, PageResult } from '../api/types'
import AppDataTable from '../components/AppDataTable.vue'
import AppPagination from '../components/AppPagination.vue'
import EmptyState from '../components/EmptyState.vue'
import PageLayout from '../layouts/PageLayout.vue'

const rows = ref<AnyRecord[]>([])
const detail = ref<AnyRecord | null>(null)
const keyword = ref('')
const loading = ref(false)
const page = ref(1)
const pageSize = ref(30)
const total = ref(0)
const activePanel = ref('markdown')
const panelOptions = [
  { label: 'Markdown', value: 'markdown' },
  { label: 'Prompt', value: 'prompt' },
  { label: '元数据', value: 'meta' }
]
const columns = [
  { key: 'date', label: '日期', minWidth: 108, slotName: 'dateLink' },
  { key: 'model_name', label: '模型', minWidth: 112 },
  { key: 'created_at', label: '生成时间', minWidth: 128, formatter: (row: AnyRecord) => timeText(row.created_at) }
]
const panelText = computed(() => {
  if (!detail.value) return ''
  if (activePanel.value === 'prompt') return String(detail.value.prompt_text || '')
  if (activePanel.value === 'meta') {
    return JSON.stringify({
      id: detail.value.id,
      date: detail.value.date,
      model_name: detail.value.model_name,
      created_at: detail.value.created_at,
      material_summary: detail.value.material_summary,
      source_counts_json: detail.value.source_counts_json
    }, null, 2)
  }
  return String(detail.value.report_markdown || '')
})

function loadFirstPage() {
  page.value = 1
  load()
}

function changePageSize(size: number) {
  pageSize.value = size
  page.value = 1
  load()
}

function changePage(nextPage: number) {
  page.value = nextPage
  load()
}

async function load() {
  loading.value = true
  try {
    const data = await callBridge<PageResult<AnyRecord>>('get_report_history', { page: page.value, page_size: pageSize.value, keyword: keyword.value })
    rows.value = data.items
    total.value = data.total
    if (!detail.value && rows.value.length) await selectReport(rows.value[0])
  } finally {
    loading.value = false
  }
}

async function selectReport(row: AnyRecord) {
  detail.value = await callBridge<AnyRecord>('get_report_detail', { report_id: row.id })
}

function timeText(value: unknown) {
  const text = String(value || '')
  return text.length >= 19 ? text.replace('T', ' ').slice(0, 19) : text || '-'
}

onMounted(load)
</script>
