<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-black tracking-tight">历史日报</h2>
        <p class="mt-2 text-slate-500">查看、检索和复制已经保存的 Markdown 日报。</p>
      </div>
      <div class="flex gap-3">
        <input v-model="keyword" class="control w-80" placeholder="搜索模型、Prompt 或日报内容" @keyup.enter="load" />
        <button class="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-bold text-white" @click="load">搜索</button>
      </div>
    </div>

    <div class="grid grid-cols-[420px_1fr] gap-5">
      <section class="card p-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="section-title">日报列表</h3>
          <StatusBadge :label="`共 ${total} 条`" />
        </div>
        <DataTable :columns="columns" :rows="rows" :loading="loading" empty-text="暂无历史日报">
          <template #date="{ row }">
            <button class="font-bold text-blue-600 hover:underline" @click="selectReport(Number(row.id))">{{ row.date || '-' }}</button>
          </template>
        </DataTable>
        <div class="mt-4 flex items-center justify-between text-sm text-slate-500">
          <span>第 {{ page }} 页</span>
          <div class="flex gap-2">
            <button class="pager" :disabled="page <= 1" @click="page--; load()">上一页</button>
            <button class="pager" :disabled="rows.length < pageSize" @click="page++; load()">下一页</button>
          </div>
        </div>
      </section>

      <section class="card min-h-[690px] p-5">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="section-title">日报内容</h3>
            <p class="mt-1 text-sm text-slate-500">{{ detail?.model_name || '选择左侧日报查看详情' }}</p>
          </div>
          <div class="flex gap-2">
            <button class="small-tab" :class="{ active: activePanel === 'markdown' }" @click="activePanel = 'markdown'">Markdown</button>
            <button class="small-tab" :class="{ active: activePanel === 'prompt' }" @click="activePanel = 'prompt'">Prompt</button>
            <button class="small-tab" :class="{ active: activePanel === 'meta' }" @click="activePanel = 'meta'">元数据</button>
          </div>
        </div>
        <pre v-if="detail" class="h-[590px] overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-7 text-slate-800">{{ panelText }}</pre>
        <EmptyState v-else title="请选择日报" description="点击左侧日期即可加载日报正文、Prompt 与元数据。" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { callBridge } from '../api/bridge'
import type { AnyRecord, PageResult } from '../api/types'
import DataTable from '../components/DataTable.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'

const rows = ref<AnyRecord[]>([])
const detail = ref<AnyRecord | null>(null)
const keyword = ref('')
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const activePanel = ref<'markdown' | 'prompt' | 'meta'>('markdown')
const columns = [
  { key: 'date', label: '日期' },
  { key: 'model_name', label: '模型' },
  { key: 'created_at', label: '生成时间' }
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

async function load() {
  loading.value = true
  try {
    const data = await callBridge<PageResult<AnyRecord>>('get_report_history', { page: page.value, page_size: pageSize, keyword: keyword.value })
    rows.value = data.items
    total.value = data.total
    if (!detail.value && rows.value.length) await selectReport(Number(rows.value[0].id))
  } finally {
    loading.value = false
  }
}

async function selectReport(id: number) {
  detail.value = await callBridge<AnyRecord>('get_report_detail', { report_id: id })
}

onMounted(load)
</script>

<style scoped>
.control {
  height: 42px;
  border-radius: 13px;
  border: 1px solid #dbe3ef;
  background: white;
  padding: 0 14px;
  font-size: 14px;
  outline: none;
}

.pager,
.small-tab {
  border-radius: 12px;
  border: 1px solid #dbe3ef;
  background: white;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 800;
  color: #475569;
}

.small-tab.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.pager:disabled {
  cursor: not-allowed;
  opacity: .45;
}
</style>
