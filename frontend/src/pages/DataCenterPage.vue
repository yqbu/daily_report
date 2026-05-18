<template>
  <PageLayout title="数据中心" subtitle="统一查看与管理应用、剪贴板、浏览与 AI 提问记录">
    <div class="flex h-full min-h-0 min-w-0 flex-col gap-4 overflow-hidden">
      <div class="flex shrink-0 items-center justify-between gap-4">
        <div class="segmented">
          <button v-for="tab in tabs" :key="tab.key" :class="{ active: activeTab === tab.key }" @click="switchTab(tab.key)">
            <el-icon><component :is="tab.icon" /></el-icon>
            <span>{{ tab.label }}</span>
          </button>
        </div>
      </div>

      <section class="app-card shrink-0 p-4">
        <div class="flex min-w-0 flex-wrap items-center gap-3">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="~"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            :clearable="false"
            style="width: 280px"
            @change="loadFirstPage"
          />
          <el-select v-model="filters.type" placeholder="类型" style="width: 128px" @change="loadFirstPage">
            <el-option label="全部类型" value="" />
            <el-option v-for="item in typeOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-if="activeTab === 'app'"
            v-model="filters.app_name"
            filterable
            placeholder="全部应用"
            style="width: 180px"
            @change="loadFirstPage"
          >
            <el-option label="全部应用" value="" />
            <el-option v-for="name in options.app_names" :key="name" :label="name" :value="name" />
          </el-select>
          <el-select
            v-if="activeTab === 'browser'"
            v-model="filters.domain"
            filterable
            placeholder="全部域名"
            style="width: 180px"
            @change="loadFirstPage"
          >
            <el-option label="全部域名" value="" />
            <el-option v-for="domain in options.domains" :key="domain" :label="domain" :value="domain" />
          </el-select>
          <el-select
            v-if="activeTab === 'ai'"
            v-model="filters.platform"
            filterable
            placeholder="全部平台"
            style="width: 180px"
            @change="loadFirstPage"
          >
            <el-option label="全部平台" value="" />
            <el-option v-for="platform in options.platforms" :key="platform" :label="platform" :value="platform" />
          </el-select>
          <el-input
            v-model="filters.keyword"
            :prefix-icon="Search"
            clearable
            placeholder="搜索应用名、进程名、窗口标题、内容..."
            class="min-w-0 flex-1"
            @keyup.enter="loadFirstPage"
            @clear="loadFirstPage"
          />
          <el-switch v-model="filters.hideSensitive" active-text="隐藏敏感内容" @change="loadFirstPage" />
          <el-switch v-if="activeTab === 'browser'" v-model="filters.hideNoise" active-text="隐藏噪声" @change="loadFirstPage" />
          <el-button class="primary-gradient" :icon="Refresh" @click="load">刷新</el-button>
        </div>
      </section>

      <section class="app-card flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden p-4">
        <div class="mb-3 flex shrink-0 items-center justify-between gap-3">
          <div class="min-w-0">
            <h3 class="section-title truncate">{{ activeLabel }}</h3>
            <p class="mt-1 text-sm text-slate-500">点击任意行打开右侧详情抽屉，表格内容在内部滚动。</p>
          </div>
          <el-tag effect="light" round>共 {{ pagination.total }} 条</el-tag>
        </div>
        <AppDataTable
          :rows="rows"
          :columns="columns"
          :loading="loading"
          row-key="id"
          height="100%"
          empty-text="当前筛选条件下暂无数据"
          @row-click="showDetail"
        >
          <template #selected="{ row }">
            <el-tag :type="row.is_selected ? 'primary' : 'info'" effect="light" round>{{ row.is_selected ? '已选' : '未选' }}</el-tag>
          </template>
          <template #kind="{ row }">
            <el-tag :type="kindTag(row)" effect="light" round>{{ recordKind(row) }}</el-tag>
          </template>
          <template #sensitive="{ row }">
            <el-tag :type="row.is_sensitive ? 'danger' : 'success'" effect="light" round>{{ row.is_sensitive ? '敏感' : '正常' }}</el-tag>
          </template>
        </AppDataTable>
        <AppPagination
          :page="pagination.page"
          :page-size="pagination.page_size"
          :total="pagination.total"
          @size-change="changePageSize"
          @current-change="changePage"
        />
      </section>
    </div>

    <el-drawer
      v-model="detailVisible"
      title="详情"
      direction="rtl"
      size="460px"
      append-to-body
      destroy-on-close
    >
      <div v-if="selectedRecord" class="flex h-full min-h-0 flex-col overflow-hidden">
        <div class="shrink-0 border-b border-slate-100 pb-4">
          <div class="flex items-start gap-3">
            <div class="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-blue-50 text-blue-600">
              <el-icon :size="24"><component :is="activeTabMeta.icon" /></el-icon>
            </div>
            <div class="min-w-0 flex-1">
              <h3 class="safe-text text-base font-black text-slate-900">{{ detailTitle }}</h3>
              <div class="mt-2 flex flex-wrap gap-2">
                <el-tag effect="light" round>{{ activeLabel }}</el-tag>
                <el-tag :type="selectedRecord.is_sensitive ? 'danger' : 'success'" effect="light" round>
                  {{ selectedRecord.is_sensitive ? '敏感内容' : '普通记录' }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-auto py-4">
          <dl class="space-y-3 text-sm">
            <div v-for="item in detailFields" :key="item.label" class="rounded-lg border border-slate-100 bg-slate-50/80 p-3">
              <dt class="text-xs font-bold text-slate-500">{{ item.label }}</dt>
              <dd class="safe-text mt-1 font-semibold text-slate-800">{{ item.value || '-' }}</dd>
            </div>
          </dl>
        </div>

        <div class="grid shrink-0 grid-cols-2 gap-3 border-t border-slate-100 pt-4">
          <el-button class="glass-button" :icon="CopyDocument">复制内容</el-button>
          <el-button type="danger" plain :icon="Delete">忽略此条</el-button>
        </div>
      </div>
    </el-drawer>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ChatDotRound,
  CopyDocument,
  Delete,
  Grid,
  Monitor,
  Refresh,
  Search
} from '@element-plus/icons-vue'
import { callBridge } from '../api/bridge'
import type { AnyRecord, PageResult } from '../api/types'
import AppDataTable from '../components/AppDataTable.vue'
import AppPagination from '../components/AppPagination.vue'
import PageLayout from '../layouts/PageLayout.vue'
import { useAppStore } from '../stores/app'

type TabKey = 'app' | 'clipboard' | 'browser' | 'ai'

const app = useAppStore()
const tabs = [
  { key: 'app' as TabKey, label: '应用记录', method: 'get_app_sessions', icon: Grid },
  { key: 'clipboard' as TabKey, label: '剪贴板', method: 'get_clipboard_entries', icon: CopyDocument },
  { key: 'browser' as TabKey, label: '浏览记录', method: 'get_browser_entries', icon: Monitor },
  { key: 'ai' as TabKey, label: 'AI 提问', method: 'get_ai_prompt_entries', icon: ChatDotRound }
]

const today = app.currentDate
const activeTab = ref<TabKey>('app')
const rows = ref<AnyRecord[]>([])
const loading = ref(false)
const selectedRecord = ref<AnyRecord | null>(null)
const detailVisible = ref(false)
const filters = reactive({
  dateRange: [today, today],
  keyword: '',
  type: '',
  app_name: '',
  domain: '',
  platform: '',
  hideSensitive: false,
  hideNoise: true
})
const pagination = reactive({ page: 1, page_size: 30, total: 0 })
const options = reactive({ app_names: [] as string[], domains: [] as string[], platforms: [] as string[] })

const activeTabMeta = computed(() => tabs.find((tab) => tab.key === activeTab.value) || tabs[0])
const activeLabel = computed(() => activeTabMeta.value.label)
const typeOptions = computed(() => tabs.map((tab) => tab.label))
const columns = computed(() => {
  const common = [
    { key: 'is_selected', label: '状态', width: 86, slotName: 'selected' },
    { key: '__kind', label: '类型', width: 98, slotName: 'kind' }
  ]
  if (activeTab.value === 'app') return [
    ...common,
    { key: 'start_time', label: '开始时间', minWidth: 160, formatter: (row: AnyRecord) => timeText(row.start_time) },
    { key: 'app_name', label: '应用', minWidth: 140 },
    { key: 'process_name', label: '进程', minWidth: 150 },
    { key: 'window_title', label: '窗口标题', minWidth: 280 },
    { key: 'active_duration_sec', label: '时长', width: 100, formatter: (row: AnyRecord) => secondsText(row.active_duration_sec) }
  ]
  if (activeTab.value === 'clipboard') return [
    ...common,
    { key: 'last_seen_at', label: '最近出现', minWidth: 160, formatter: (row: AnyRecord) => timeText(row.last_seen_at) },
    { key: 'content_preview', label: '内容预览', minWidth: 360 },
    { key: 'char_count', label: '字数', width: 90 },
    { key: 'seen_count', label: '次数', width: 90 },
    { key: 'is_sensitive', label: '敏感', width: 90, slotName: 'sensitive' }
  ]
  if (activeTab.value === 'browser') return [
    ...common,
    { key: 'visit_time', label: '访问时间', minWidth: 160, formatter: (row: AnyRecord) => timeText(row.visit_time) },
    { key: 'title', label: '标题 / 搜索词', minWidth: 320, formatter: (row: AnyRecord) => browserTitle(row) },
    { key: 'domain', label: '域名', minWidth: 160 },
    { key: 'browser', label: '浏览器', width: 110 },
    { key: 'visit_duration_sec', label: '停留', width: 100, formatter: (row: AnyRecord) => secondsText(row.visit_duration_sec) }
  ]
  return [
    ...common,
    { key: 'timestamp', label: '时间', minWidth: 160, formatter: (row: AnyRecord) => timeText(row.timestamp) },
    { key: 'platform', label: '平台', minWidth: 130 },
    { key: 'prompt_preview', label: '提问预览', minWidth: 360 },
    { key: 'page_title', label: '页面标题', minWidth: 220 },
    { key: 'is_sensitive', label: '敏感', width: 90, slotName: 'sensitive' }
  ]
})
const detailTitle = computed(() => {
  const row = selectedRecord.value
  if (!row) return ''
  return String(row.window_title || row.title || row.prompt_preview || row.content_preview || row.app_name || '记录详情')
})
const detailFields = computed(() => {
  const row = selectedRecord.value || {}
  return [
    { label: '类型', value: activeLabel.value },
    { label: '应用 / 平台', value: row.app_name || row.platform || row.browser || row.domain || '本地' },
    { label: '开始时间', value: row.start_time || row.first_seen_at || row.visit_time || row.timestamp || row.last_seen_at },
    { label: '结束时间', value: row.end_time || row.last_seen_at },
    { label: '时长 / 字数', value: row.active_duration_sec ? secondsText(row.active_duration_sec) : row.char_count },
    { label: '窗口标题', value: row.window_title || row.page_title || row.title },
    { label: '来源 / 域名', value: row.process_name || row.domain || row.source || row.profile_name },
    { label: '内容预览', value: row.content_preview || row.prompt_preview || browserTitle(row) || row.url },
    { label: '标签', value: row.is_search ? '搜索记录' : row.is_noise ? '噪声' : row.is_selected ? '已选素材' : '未选' }
  ]
})

function switchTab(tab: TabKey) {
  activeTab.value = tab
  pagination.page = 1
  selectedRecord.value = null
  detailVisible.value = false
  load()
}

function loadFirstPage() {
  pagination.page = 1
  load()
}

function changePageSize(size: number) {
  pagination.page_size = size
  pagination.page = 1
  load()
}

function changePage(page: number) {
  pagination.page = page
  load()
}

async function load() {
  loading.value = true
  try {
    const data = await callBridge<PageResult<AnyRecord>>(activeTabMeta.value.method, {
      date: filters.dateRange[1] || filters.dateRange[0] || app.currentDate,
      keyword: filters.keyword,
      app_name: filters.app_name,
      domain: filters.domain,
      platform: filters.platform,
      hideSensitive: filters.hideSensitive,
      hideNoise: filters.hideNoise,
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

function showDetail(row: AnyRecord) {
  selectedRecord.value = row
  detailVisible.value = true
}

function recordKind(row: AnyRecord) {
  if (activeTab.value === 'browser') return row.is_search ? '搜索' : '浏览'
  return activeLabel.value.replace('记录', '')
}

function kindTag(row: AnyRecord) {
  if (activeTab.value === 'clipboard') return 'warning'
  if (activeTab.value === 'browser') return row.is_search ? 'primary' : 'success'
  if (activeTab.value === 'ai') return 'danger'
  return 'primary'
}

function browserTitle(row: AnyRecord) {
  return row.is_search ? `${row.search_engine || '搜索'}：${row.search_query || ''}` : String(row.title || row.url || '')
}

function timeText(value: unknown) {
  const text = String(value || '')
  return text.length >= 19 ? text.replace('T', ' ').slice(0, 19) : text || '-'
}

function secondsText(value: unknown) {
  const seconds = Math.round(Number(value || 0))
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  if (seconds >= 60) return `${Math.floor(seconds / 60)}m`
  return `${seconds}s`
}

onMounted(load)
</script>

<style scoped>
.segmented {
  display: inline-flex;
  gap: 4px;
  max-width: 100%;
  overflow: hidden;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
  padding: 4px;
  box-shadow: var(--app-shadow);
}

.segmented button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 150px;
  justify-content: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  padding: 12px 18px;
  color: #475569;
  font-weight: 800;
  cursor: pointer;
}

.segmented button.active {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.22);
}
</style>
