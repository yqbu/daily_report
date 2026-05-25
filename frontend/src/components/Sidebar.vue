<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, shallowRef } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  Calendar,
  Connection,
  DataAnalysis,
  Document,
  Search,
  Setting
} from '@element-plus/icons-vue'

import { callBridge } from '../api/bridge'
import appIcon from '../assets/icon-64-tb.png'

type CollectorStatus = 'checking' | 'running' | 'stopped'
type CollectorStatusPayload = Record<string, unknown>

const props = defineProps<{
  expanded: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()

const route = useRoute()
const router = useRouter()
const searchKeyword = shallowRef('')
const collectorStatus = shallowRef<CollectorStatus>('checking')
const collectorBusy = shallowRef(false)
let statusTimer: number | undefined

const navItems = [
  {
    to: '/',
    name: 'today',
    label: '今日总览',
    icon: Calendar
  },
  {
    to: '/data',
    name: 'data-center',
    label: '数据中心',
    icon: DataAnalysis
  },
  {
    to: '/reports',
    name: 'report-workbench',
    label: '日报工作台',
    icon: Document
  },
  {
    to: '/settings',
    name: 'settings',
    label: '设置',
    icon: Setting
  }
] as const

const activeRouteName = computed(() => String(route.name || 'today'))
const collectorRunning = computed(() => collectorStatus.value === 'running')
const collectorStatusLabel = computed(() => {
  if (collectorBusy.value || collectorStatus.value === 'checking') return '状态检查中'
  return collectorRunning.value ? '采集器运行中' : '采集器未启动'
})
const collectorActionTitle = computed(() => {
  if (collectorBusy.value) return '正在切换采集器状态'
  return collectorRunning.value ? '停止采集器服务' : '启动采集器服务'
})
const normalizedSearch = computed(() => searchKeyword.value.trim().toLowerCase())
const searchMatches = computed(() => {
  const keyword = normalizedSearch.value
  if (!keyword) return navItems

  return navItems.filter((item) => {
    return item.label.toLowerCase().includes(keyword) || item.name.includes(keyword)
  })
})

function handleSearchShellClick(): void {
  if (!props.expanded) {
    emit('toggle')
  }
}

function openFirstSearchMatch(): void {
  const [firstMatch] = searchMatches.value
  if (!firstMatch) return

  router.push(firstMatch.to)
  searchKeyword.value = ''
}

function openSearchMatch(to: string): void {
  router.push(to)
  searchKeyword.value = ''
}

async function refreshCollectorStatus(): Promise<void> {
  try {
    const payload = await callBridge<CollectorStatusPayload>('get_collector_status', {})
    collectorStatus.value = isCollectorRunning(payload) ? 'running' : 'stopped'
  } catch {
    collectorStatus.value = 'stopped'
  }
}

async function toggleCollectorService(): Promise<void> {
  if (collectorBusy.value) return

  collectorBusy.value = true
  try {
    const targetRunning = !collectorRunning.value
    const method = targetRunning ? 'start_collector_service' : 'stop_collector_service'
    await callBridge(method, {})
    await waitForCollectorStatus(targetRunning)
  } finally {
    collectorBusy.value = false
  }
}

function isCollectorRunning(payload: CollectorStatusPayload): boolean {
  const directStatus = readStatusText(payload)
  if (directStatus) return isRunningStatusText(directStatus)

  const directFlag = readRunningFlag(payload)
  if (directFlag !== null) return directFlag

  return isRunningStatusText(JSON.stringify(payload))
}

function readStatusText(payload: CollectorStatusPayload): string {
  const keys = ['collector_status', 'status', 'state', 'service_state']
  for (const key of keys) {
    const value = payload[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return ''
}

function readRunningFlag(payload: CollectorStatusPayload): boolean | null {
  const keys = ['running', 'is_running', 'active', 'is_active', 'collector_running']
  for (const key of keys) {
    const value = payload[key]
    if (typeof value === 'boolean') return value
  }
  return null
}

function isRunningStatusText(value: string): boolean {
  const text = value.toLowerCase()
  if (/(stopped|stop|offline|inactive|not_running|not running|disabled|dead|failed)/.test(text)) {
    return false
  }
  return /(running|started|online|active|healthy|enabled|ok)/.test(text)
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function waitForCollectorStatus(targetRunning: boolean): Promise<void> {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    await wait(700)
    await refreshCollectorStatus()
    if (collectorRunning.value === targetRunning) {
      return
    }
  }
}

onMounted(() => {
  refreshCollectorStatus()
  statusTimer = window.setInterval(refreshCollectorStatus, 12000)
})

onBeforeUnmount(() => {
  if (statusTimer !== undefined) {
    window.clearInterval(statusTimer)
  }
})
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar--expanded': props.expanded }">
    <button
      class="brand"
      type="button"
      :title="props.expanded ? '折叠菜单' : '展开菜单'"
      :aria-label="props.expanded ? '折叠菜单' : '展开菜单'"
      @click="emit('toggle')"
    >
      <span class="brand-logo-wrap">
        <img class="brand-logo" :src="appIcon" alt="" />
      </span>

      <span class="brand-copy">
        <span class="brand-title">Daily Report</span>
        <span class="brand-subtitle">本地工作日报</span>
      </span>

<!--      <span class="brand-toggle">-->
<!--        <ArrowLeft v-if="props.expanded" class="toggle-icon" />-->
<!--        <ArrowRight v-else class="toggle-icon" />-->
<!--      </span>-->
    </button>

    <div class="search-block">
      <form
        class="quick-search"
        role="search"
        :title="props.expanded ? '搜索功能界面' : '展开搜索'"
        @submit.prevent="openFirstSearchMatch"
        @click="handleSearchShellClick"
      >
        <Search class="search-icon" />
        <input
          v-model="searchKeyword"
          class="search-input"
          type="search"
          placeholder="搜索功能"
          autocomplete="off"
          :aria-hidden="!props.expanded"
          :tabindex="props.expanded ? 0 : -1"
        />
        <span class="search-shortcut">Ctrl K</span>
      </form>

      <div v-if="props.expanded && normalizedSearch" class="search-results">
        <button
          v-for="item in searchMatches"
          :key="item.name"
          class="search-result"
          type="button"
          @click="openSearchMatch(item.to)"
        >
          <component :is="item.icon" class="search-result-icon" />
          <span>{{ item.label }}</span>
        </button>

        <div v-if="searchMatches.length === 0" class="search-empty">没有匹配的功能</div>
      </div>
    </div>

    <nav class="nav-list" aria-label="主导航">
      <RouterLink
        v-for="item in navItems"
        :key="item.name"
        class="nav-item"
        :class="{ 'nav-item--active': activeRouteName === item.name }"
        :to="item.to"
        :title="item.label"
      >
        <component :is="item.icon" class="nav-icon" />
        <span class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <button
      class="bridge-status"
      :class="{
        'bridge-status--online': collectorRunning,
        'bridge-status--offline': !collectorRunning,
        'bridge-status--busy': collectorBusy || collectorStatus === 'checking'
      }"
      type="button"
      :title="collectorActionTitle"
      :aria-label="collectorActionTitle"
      :disabled="collectorBusy"
      @click="toggleCollectorService"
    >
      <Connection class="bridge-icon" />
      <span class="bridge-label">{{ collectorStatusLabel }}</span>
    </button>
  </aside>
</template>

<style scoped>
.sidebar {
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 14px;
  padding: 14px;
  border-right: 1px solid #dce3ee;
  background: rgba(255, 255, 255, 0.9);
  overflow: hidden;
}

.brand,
.quick-search,
.nav-item,
.bridge-status {
  width: 56px;
  min-width: 0;
  border-radius: 8px;
}

.brand {
  height: 56px;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) 32px;
  align-items: center;
  gap: 0;
  padding: 0;
  border: 0;
  color: #ffffff;
  background: transparent;
  cursor: pointer;
  overflow: hidden;
  transition:
    width 240ms cubic-bezier(0.22, 1, 0.36, 1),
    gap 240ms cubic-bezier(0.22, 1, 0.36, 1),
    background-color 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease;
}

.brand-logo-wrap {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #172033;
  box-shadow: 0 12px 28px rgba(23, 32, 51, 0.18);
}

.brand-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
}

.brand-copy {
  min-width: 0;
  display: grid;
  gap: 3px;
  overflow: hidden;
  text-align: left;
  opacity: 0;
  transform: translateX(-6px);
  transition:
    opacity 120ms ease,
    transform 160ms ease;
}

.brand-title {
  color: #172033;
  font-size: 15px;
  font-weight: 760;
  line-height: 1.15;
  white-space: nowrap;
}

.brand-subtitle {
  color: #667085;
  font-size: 12px;
  line-height: 1.2;
  white-space: nowrap;
}

.brand-toggle {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #526179;
  background: #ffffff;
  opacity: 0;
  transform: translateX(-6px);
  transition:
    opacity 120ms ease,
    transform 160ms ease,
    color 160ms ease,
    border-color 160ms ease,
    background-color 160ms ease;
}

.brand:hover .brand-toggle {
  color: #2563eb;
  border-color: #c9dcff;
  background: #eff6ff;
}

.toggle-icon,
.search-icon,
.nav-icon,
.bridge-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
}

.search-block {
  min-width: 0;
  display: grid;
  gap: 8px;
}

.quick-search {
  height: 36px;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  align-items: center;
  gap: 0;
  padding: 0;
  border: 1px solid #dce3ee;
  color: #526179;
  background: #f8fafc;
  cursor: text;
  overflow: hidden;
  transition:
    width 240ms cubic-bezier(0.22, 1, 0.36, 1),
    gap 240ms cubic-bezier(0.22, 1, 0.36, 1),
    padding 240ms cubic-bezier(0.22, 1, 0.36, 1),
    background-color 160ms ease,
    border-color 160ms ease;
}

.quick-search:hover {
  border-color: #c9dcff;
  background: #eff6ff;
}

.search-icon {
  justify-self: center;
}

.search-input {
  min-width: 0;
  width: 100%;
  border: 0;
  outline: 0;
  color: #172033;
  background: transparent;
  font-size: 13px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 120ms ease;
}

.search-input::placeholder {
  color: #98a2b3;
}

.search-shortcut {
  padding: 3px 5px;
  border: 1px solid #dce3ee;
  border-radius: 6px;
  color: #667085;
  background: #ffffff;
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
  opacity: 0;
  transform: translateX(-6px);
  transition:
    opacity 120ms ease,
    transform 160ms ease;
}

.search-results {
  display: grid;
  gap: 4px;
  padding: 6px;
  border: 1px solid #e6ebf3;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.08);
}

.search-result {
  height: 36px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  border: 0;
  border-radius: 6px;
  color: #344054;
  background: transparent;
  font-size: 13px;
  font-weight: 650;
  text-align: left;
  cursor: pointer;
}

.search-result:hover {
  color: #2563eb;
  background: #eff6ff;
}

.search-result-icon {
  width: 16px;
  height: 16px;
}

.search-empty {
  padding: 8px;
  color: #98a2b3;
  font-size: 12px;
}

.nav-list {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  justify-content: flex-start;
}

.nav-item,
.bridge-status {
  height: 48px;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: center;
  justify-items: start;
  border: 1px solid transparent;
  color: #667085;
  text-decoration: none;
  background: transparent;
  transition:
    width 240ms cubic-bezier(0.22, 1, 0.36, 1),
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.nav-item {
  position: relative;
  overflow: visible;
}

.nav-icon,
.bridge-icon {
  justify-self: center;
}

.nav-item:hover {
  color: #2563eb;
  background: #f2f6ff;
  border-color: #d8e5ff;
}

.nav-item--active {
  color: #2563eb;
  background: #eaf1ff;
  border-color: #c9dcff;
  box-shadow: inset 3px 0 0 #2563eb;
}

.nav-label {
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  z-index: 20;
  width: max-content;
  max-width: 132px;
  transform: translateY(-50%);
  padding: 6px 8px;
  border: 1px solid #dce3ee;
  border-radius: 6px;
  color: #172033;
  background: #ffffff;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
  opacity: 0;
  pointer-events: none;
  transition: opacity 120ms ease;
}

.nav-item:hover .nav-label,
.nav-item:focus-visible .nav-label {
  opacity: 1;
}

.bridge-status {
  padding: 0;
  overflow: hidden;
  cursor: pointer;
}

.bridge-label {
  display: none;
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 650;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 120ms ease;
}

.bridge-status--online {
  color: #10b981;
  background: #ecfdf5;
  border-color: #bbf7d0;
}

.bridge-status--online .bridge-label {
  color: #047857;
}

.bridge-status--offline {
  color: #98a2b3;
  background: #f8fafc;
  border-color: #e4e7ec;
}

.bridge-status--offline .bridge-label {
  color: #667085;
}

.bridge-status--busy {
  color: #667085;
  background: #f9fafb;
  border-color: #e4e7ec;
}

.bridge-status:disabled {
  cursor: wait;
}

.sidebar--expanded .brand,
.sidebar--expanded .quick-search,
.sidebar--expanded .nav-item,
.sidebar--expanded .bridge-status {
  width: 100%;
}

.sidebar--expanded .brand {
  gap: 10px;
  padding-right: 10px;
  border: 1px solid #dce3ee;
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
}

.sidebar--expanded .brand-copy,
.sidebar--expanded .brand-toggle,
.sidebar--expanded .search-input,
.sidebar--expanded .search-shortcut,
.sidebar--expanded .bridge-label {
  opacity: 1;
  transform: translateX(0);
  pointer-events: auto;
  transition-delay: 110ms;
}

.sidebar--expanded .quick-search {
  gap: 12px;
  padding: 0 10px 0 14px;
  grid-template-columns: 24px minmax(0, 1fr) auto;
}

.sidebar--expanded .nav-list {
  align-items: stretch;
}

.sidebar--expanded .nav-item,
.sidebar--expanded .bridge-status {
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: center;
  justify-items: start;
  gap: 12px;
  padding: 0 14px;
  overflow: hidden;
}

.sidebar--expanded .nav-label {
  position: static;
  width: auto;
  max-width: none;
  transform: none;
  padding: 0;
  border: 0;
  color: #344054;
  background: transparent;
  font-size: 14px;
  font-weight: 650;
  line-height: 1;
  box-shadow: none;
  opacity: 0;
  transition: opacity 120ms ease 110ms;
}

.sidebar--expanded .nav-item .nav-label {
  pointer-events: auto;
  opacity: 1;
}

.sidebar--expanded .nav-item--active .nav-label {
  color: #1d4ed8;
}

.sidebar--expanded .bridge-label {
  display: block;
}

@media (max-width: 820px) {
  .sidebar {
    min-height: auto;
    grid-template-columns: auto auto minmax(0, 1fr) auto;
    grid-template-rows: auto;
    align-items: center;
    padding: 10px 12px;
    border-top: 1px solid #dce3ee;
    border-right: 0;
  }

  .brand,
  .quick-search,
  .nav-item,
  .bridge-status {
    width: 46px;
    height: 46px;
  }

  .brand {
    grid-template-columns: 46px;
  }

  .brand-logo-wrap {
    width: 46px;
    height: 46px;
  }

  .brand-logo {
    width: 30px;
    height: 30px;
  }

  .search-block {
    display: none;
  }

  .nav-list {
    flex-direction: row;
    justify-content: center;
  }

  .nav-label,
  .brand-copy,
  .brand-toggle,
  .bridge-label {
    display: none;
  }
}
</style>
