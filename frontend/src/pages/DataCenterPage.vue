<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-black tracking-tight">数据中心</h2>
        <p class="mt-2 text-slate-500">统一查看应用、剪贴板、浏览记录与 AI 提问。</p>
      </div>
      <div class="flex gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-card">
        <button v-for="tab in tabs" :key="tab.key" class="tab-button" :class="{ active: activeTab === tab.key }" @click="switchTab(tab.key)">
          {{ tab.label }}
        </button>
      </div>
    </div>

    <section class="card p-5">
      <div class="flex flex-wrap items-center gap-3">
        <input v-model="filters.date" type="date" class="control w-44" @change="load" />
        <input v-model="filters.keyword" class="control min-w-72 flex-1" placeholder="搜索标题、内容、来源或关键词" @keyup.enter="load" />
        <select v-if="activeTab === 'app'" v-model="filters.app_name" class="control w-48" @change="load">
          <option value="">全部应用</option>
          <option v-for="name in options.app_names" :key="name" :value="name">{{ name }}</option>
        </select>
        <select v-if="activeTab === 'browser'" v-model="filters.domain" class="control w-48" @change="load">
          <option value="">全部域名</option>
          <option v-for="domain in options.domains" :key="domain" :value="domain">{{ domain }}</option>
        </select>
        <select v-if="activeTab === 'ai'" v-model="filters.platform" class="control w-48" @change="load">
          <option value="">全部平台</option>
          <option v-for="platform in options.platforms" :key="platform" :value="platform">{{ platform }}</option>
        </select>
        <button class="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-blue-700" @click="load">刷新</button>
      </div>
    </section>

    <section class="grid grid-cols-[1fr_300px] gap-5">
      <div class="card p-5">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="section-title">{{ activeLabel }}</h3>
            <p class="mt-1 text-sm text-slate-500">默认分页加载，每页 {{ pagination.page_size }} 条。</p>
          </div>
          <StatusBadge :label="`共 ${pagination.total} 条`" />
        </div>
        <DataTable :columns="columns" :rows="rows" :loading="loading" empty-text="当前筛选条件下暂无数据">
          <template #is_sensitive="{ row }">
            <StatusBadge :label="row.is_sensitive ? '敏感' : '正常'" :tone="row.is_sensitive ? 'red' : 'green'" />
          </template>
          <template #is_selected="{ row }">
            <StatusBadge :label="row.is_selected ? '已选' : '未选'" :tone="row.is_selected ? 'blue' : 'gray'" />
          </template>
        </DataTable>
        <div class="mt-4 flex items-center justify-between text-sm text-slate-500">
          <span>第 {{ pagination.page }} 页 / {{ totalPages }} 页</span>
          <div class="flex gap-2">
            <button class="pager" :disabled="pagination.page <= 1" @click="changePage(-1)">上一页</button>
            <button class="pager" :disabled="pagination.page >= totalPages" @click="changePage(1)">下一页</button>
          </div>
        </div>
      </div>

      <aside class="card p-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="section-title">详情</h3>
          <StatusBadge label="占位" tone="gray" />
        </div>
        <EmptyState title="选择记录查看详情" description="详情抽屉的选中联动后续接入；当前列表与筛选接口已就绪。" />
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { callBridge } from '../api/bridge'
import type { AnyRecord, PageResult } from '../api/types'
import DataTable from '../components/DataTable.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAppStore } from '../stores/app'

type TabKey = 'app' | 'clipboard' | 'browser' | 'ai'

const app = useAppStore()
const tabs: Array<{ key: TabKey; label: string; method: string }> = [
  { key: 'app', label: '应用记录', method: 'get_app_sessions' },
  { key: 'clipboard', label: '剪贴板', method: 'get_clipboard_entries' },
  { key: 'browser', label: '浏览记录', method: 'get_browser_entries' },
  { key: 'ai', label: 'AI 提问', method: 'get_ai_prompt_entries' }
]

const activeTab = ref<TabKey>('app')
const rows = ref<AnyRecord[]>([])
const loading = ref(false)
const filters = reactive({ date: app.currentDate, keyword: '', app_name: '', domain: '', platform: '' })
const pagination = reactive({ page: 1, page_size: 30, total: 0 })
const options = reactive({ app_names: [] as string[], domains: [] as string[], platforms: [] as string[] })

const activeLabel = computed(() => tabs.find((tab) => tab.key === activeTab.value)?.label || '数据')
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.total / pagination.page_size)))
const columns = computed(() => {
  if (activeTab.value === 'app') return [
    { key: 'is_selected', label: '状态' },
    { key: 'start_time', label: '开始时间' },
    { key: 'app_name', label: '应用' },
    { key: 'process_name', label: '进程' },
    { key: 'window_title', label: '窗口标题' },
    { key: 'active_duration_sec', label: '活跃秒数' }
  ]
  if (activeTab.value === 'clipboard') return [
    { key: 'is_selected', label: '状态' },
    { key: 'last_seen_at', label: '最近出现' },
    { key: 'content_preview', label: '内容预览' },
    { key: 'char_count', label: '字符数' },
    { key: 'seen_count', label: '次数' },
    { key: 'is_sensitive', label: '敏感' }
  ]
  if (activeTab.value === 'browser') return [
    { key: 'is_selected', label: '状态' },
    { key: 'visit_time', label: '访问时间' },
    { key: 'title', label: '标题' },
    { key: 'domain', label: '域名' },
    { key: 'browser', label: '浏览器' },
    { key: 'visit_duration_sec', label: '停留秒数' }
  ]
  return [
    { key: 'is_selected', label: '状态' },
    { key: 'timestamp', label: '时间' },
    { key: 'platform', label: '平台' },
    { key: 'prompt_preview', label: '提问预览' },
    { key: 'page_title', label: '页面标题' },
    { key: 'is_sensitive', label: '敏感' }
  ]
})

function switchTab(tab: TabKey) {
  activeTab.value = tab
  pagination.page = 1
  rows.value = []
  load()
}

function changePage(offset: number) {
  pagination.page = Math.min(totalPages.value, Math.max(1, pagination.page + offset))
  load()
}

async function load() {
  loading.value = true
  try {
    const tab = tabs.find((item) => item.key === activeTab.value)!
    const data = await callBridge<PageResult<AnyRecord>>(tab.method, {
      ...filters,
      page: pagination.page,
      page_size: pagination.page_size
    })
    rows.value = data.items
    pagination.total = data.total
    options.app_names = (data.app_names as string[]) || options.app_names
    options.domains = (data.domains as string[]) || options.domains
    options.platforms = (data.platforms as string[]) || options.platforms
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.tab-button {
  border-radius: 14px;
  padding: 10px 18px;
  color: #64748b;
  font-size: 14px;
  font-weight: 800;
}

.tab-button.active {
  background: #2563eb;
  color: white;
  box-shadow: 0 10px 22px rgba(37, 99, 235, .22);
}

.control {
  height: 42px;
  border-radius: 13px;
  border: 1px solid #dbe3ef;
  background: white;
  padding: 0 14px;
  font-size: 14px;
  outline: none;
}

.control:focus {
  border-color: #2563eb;
}

.pager {
  border-radius: 12px;
  border: 1px solid #dbe3ef;
  background: white;
  padding: 8px 14px;
  font-weight: 700;
  color: #475569;
}

.pager:disabled {
  cursor: not-allowed;
  opacity: .45;
}
</style>
