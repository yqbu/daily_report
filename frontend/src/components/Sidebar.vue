<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  Calendar,
  Connection,
  Cpu,
  DataAnalysis,
  Document,
  Lock,
  MagicStick,
  Monitor,
  Search,
  Setting
} from '@element-plus/icons-vue'

import appIcon from '../assets/icon-64-tb.png'

const props = defineProps<{
  expanded: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()

const route = useRoute()
const router = useRouter()
const searchKeyword = shallowRef('')
const dismissedCollapsedPopoverName = shallowRef('')

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
    icon: Document,
    children: [
      { to: '/reports?tab=generate', key: 'generate', label: '日报生成', shortLabel: '生', icon: Document },
      { to: '/reports?tab=history', key: 'history', label: '历史日报', shortLabel: '历', icon: Calendar }
    ]
  },
  {
    to: '/apps',
    name: 'app-profiles',
    label: '应用配置',
    icon: MagicStick
  },
  {
    to: '/runtime',
    name: 'runtime-center',
    label: '运行中心',
    icon: Connection
  },
  {
    to: '/settings',
    name: 'settings',
    label: '设置',
    icon: Setting,
    children: [
      { to: '/settings?tab=collector', key: 'collector', label: '采集设置', shortLabel: '采', icon: DataAnalysis },
      { to: '/settings?tab=privacy', key: 'privacy', label: '隐私规则', shortLabel: '隐', icon: Lock },
      { to: '/settings?tab=model', key: 'model', label: '模型设置', shortLabel: '模', icon: Cpu },
      { to: '/settings?tab=system', key: 'system', label: '系统集成', shortLabel: '集', icon: Monitor }
    ]
  }
] as const

const activeRouteName = computed(() => String(route.name || 'today'))
const activeSecondaryKey = computed(() => String(route.query.tab || ''))
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

  void router.push(firstMatch.to)
  searchKeyword.value = ''
}

function openSearchMatch(to: string): void {
  void router.push(to)
  searchKeyword.value = ''
}

function dismissCollapsedPopover(name: string): void {
  dismissedCollapsedPopoverName.value = name
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur()
  }
}

function resetDismissedCollapsedPopover(name: string): void {
  if (dismissedCollapsedPopoverName.value === name) {
    dismissedCollapsedPopoverName.value = ''
  }
}
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar--expanded': props.expanded }">
    <button
      class="brand"
      type="button"
      :title="props.expanded ? '收起菜单' : '展开菜单'"
      :aria-label="props.expanded ? '收起菜单' : '展开菜单'"
      @click="emit('toggle')"
    >
      <span class="brand-logo-wrap">
        <img class="brand-logo" :src="appIcon" alt="" />
      </span>

      <span class="brand-copy">
        <span class="brand-title">Daily Report</span>
        <span class="brand-subtitle">本地工作日报</span>
      </span>
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
      <div
        v-for="item in navItems"
        :key="item.name"
        class="nav-group"
        :class="{ 'nav-group--collapsed-popover-dismissed': dismissedCollapsedPopoverName === item.name }"
        @mouseleave="resetDismissedCollapsedPopover(item.name)"
      >
        <RouterLink
          class="nav-item"
          :class="{ 'nav-item--active': activeRouteName === item.name }"
          :to="item.to"
          :title="item.label"
        >
          <component :is="item.icon" class="nav-icon" />
          <span class="nav-label">{{ item.label }}</span>
          <ArrowRight
            v-if="props.expanded && 'children' in item && item.children"
            class="nav-parent-arrow"
            :class="{ 'nav-parent-arrow--expanded': activeRouteName === item.name }"
          />
        </RouterLink>

        <div
          v-if="!props.expanded && 'children' in item && item.children"
          class="collapsed-sub-nav-popover"
          :aria-label="`${item.label}次级导航`"
        >
          <span class="collapsed-sub-nav-title">{{ item.label }}</span>
          <RouterLink
            v-for="child in item.children"
            :key="child.key"
            class="collapsed-sub-nav-item"
            :class="{
              'collapsed-sub-nav-item--active':
                activeRouteName === item.name &&
                (activeSecondaryKey === child.key || (!activeSecondaryKey && child.key === item.children[0].key))
            }"
            :to="child.to"
            @click="dismissCollapsedPopover(item.name)"
          >
            <span><component :is="child.icon" /></span>
            <strong>{{ child.label }}</strong>
          </RouterLink>
        </div>

        <div
          v-if="props.expanded && 'children' in item && item.children && activeRouteName === item.name"
          class="sub-nav-list"
          :aria-label="`${item.label}次级导航`"
        >
          <RouterLink
            v-for="child in item.children"
            :key="child.key"
            class="sub-nav-item"
            :class="{
              'sub-nav-item--active':
                activeSecondaryKey === child.key || (!activeSecondaryKey && child.key === item.children[0].key)
            }"
            :to="child.to"
          >
            <component :is="child.icon" class="sub-nav-icon" />
            <span>{{ child.label }}</span>
            <ArrowRight class="sub-nav-arrow" />
          </RouterLink>
        </div>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  position: relative;
  z-index: 100;
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 14px;
  padding: 14px;
  border-right: 1px solid #dce3ee;
  background: rgba(255, 255, 255, 0.9);
  overflow: visible;
}

.brand,
.quick-search,
.nav-item {
  width: 56px;
  min-width: 0;
  border-radius: 8px;
}

.brand {
  height: 56px;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
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

.search-icon,
.nav-icon {
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
  overflow: visible;
}

.nav-group {
  width: 56px;
  min-width: 0;
  position: relative;
  display: grid;
  gap: 6px;
}

.nav-item {
  position: relative;
  height: 48px;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: center;
  justify-items: start;
  border: 1px solid transparent;
  color: #667085;
  text-decoration: none;
  background: transparent;
  overflow: visible;
  transition:
    width 240ms cubic-bezier(0.22, 1, 0.36, 1),
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.nav-icon {
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

.nav-parent-arrow {
  display: none;
}

.nav-item:hover .nav-label,
.nav-item:focus-visible .nav-label {
  opacity: 1;
}

.nav-group:has(.collapsed-sub-nav-popover):hover .nav-label,
.nav-group:has(.collapsed-sub-nav-popover):focus-within .nav-label {
  opacity: 0;
}

.sidebar--expanded .brand,
.sidebar--expanded .quick-search,
.sidebar--expanded .nav-item {
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
.sidebar--expanded .search-input,
.sidebar--expanded .search-shortcut {
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

.sidebar--expanded .nav-group {
  width: 100%;
}

.sidebar--expanded .nav-item {
  grid-template-columns: 24px minmax(0, 1fr) auto;
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

.sidebar--expanded .nav-parent-arrow {
  width: 13px;
  height: 13px;
  display: block;
  justify-self: end;
  color: #667085;
  transform: rotate(0deg);
  transition:
    color 160ms ease,
    transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.sidebar--expanded .nav-item--active .nav-parent-arrow {
  color: #2563eb;
}

.sidebar--expanded .nav-parent-arrow--expanded {
  transform: rotate(90deg);
}

.collapsed-sub-nav-popover {
  position: absolute;
  left: calc(100% + 10px);
  top: -2px;
  z-index: 60;
  width: 156px;
  display: grid;
  gap: 5px;
  padding: 8px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.14);
  opacity: 0;
  pointer-events: none;
  transform: translateX(-4px) scale(0.98);
  transform-origin: left top;
  transition:
    opacity 140ms ease,
    transform 160ms cubic-bezier(0.22, 1, 0.36, 1);
}

.collapsed-sub-nav-popover::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 0;
  width: 10px;
  height: 100%;
}

.nav-group:hover .collapsed-sub-nav-popover,
.nav-group:focus-within .collapsed-sub-nav-popover {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(0) scale(1);
}

.nav-group--collapsed-popover-dismissed:hover .collapsed-sub-nav-popover,
.nav-group--collapsed-popover-dismissed:focus-within .collapsed-sub-nav-popover {
  opacity: 0;
  pointer-events: none;
  transform: translateX(-4px) scale(0.98);
}

.collapsed-sub-nav-title {
  padding: 2px 4px 4px;
  color: #667085;
  font-size: 11px;
  font-weight: 720;
  line-height: 1;
}

.collapsed-sub-nav-item {
  min-width: 0;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 7px;
  color: #526179;
  text-decoration: none;
  transition:
    color 160ms ease,
    background-color 160ms ease;
}

.collapsed-sub-nav-item span {
  width: 22px;
  height: 22px;
  display: inline-grid;
  place-items: center;
  border: 1px solid #e3e9f3;
  border-radius: 7px;
  color: #667085;
  background: #ffffff;
  transition:
    color 160ms ease,
    border-color 160ms ease,
    background-color 160ms ease;
}

.collapsed-sub-nav-item span :deep(svg) {
  width: 14px;
  height: 14px;
}

.collapsed-sub-nav-item strong {
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 720;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collapsed-sub-nav-item:hover,
.collapsed-sub-nav-item:focus-visible {
  color: #2563eb;
  background: #f2f6ff;
  outline: 0;
}

.collapsed-sub-nav-item:hover span,
.collapsed-sub-nav-item:focus-visible span {
  color: #2563eb;
  border-color: #cfe0ff;
  background: #eff6ff;
}

.collapsed-sub-nav-item--active {
  color: #1d4ed8;
  background: #eff6ff;
}

.collapsed-sub-nav-item--active span {
  color: #1d4ed8;
  border-color: #bfdbfe;
  background: #dbeafe;
}

.sub-nav-list {
  display: grid;
  gap: 8px;
  margin-top: 2px;
  padding: 10px;
  border: 1px solid #e6ebf3;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.74);
}

.sub-nav-item {
  min-width: 0;
  min-height: 42px;
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border: 1px solid #e3e9f3;
  border-radius: 7px;
  color: #526179;
  background: #ffffff;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
  text-decoration: none;
  white-space: nowrap;
  transition:
    color 160ms ease,
    border-color 160ms ease,
    background-color 160ms ease,
    box-shadow 160ms ease;
}

.sub-nav-icon,
.sub-nav-arrow {
  width: 16px;
  height: 16px;
  color: #667085;
  transition: color 160ms ease;
}

.sub-nav-icon {
  justify-self: center;
}

.sub-nav-arrow {
  justify-self: end;
  opacity: 0.78;
}

.sub-nav-item span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sub-nav-item:hover {
  color: #2563eb;
  border-color: #cfe0ff;
  background: #f2f6ff;
}

.sub-nav-item:hover .sub-nav-icon,
.sub-nav-item:hover .sub-nav-arrow {
  color: #2563eb;
}

.sub-nav-item--active {
  color: #1d4ed8;
  border-color: #c7dcff;
  background: #eef5ff;
  box-shadow: inset 2px 0 0 #409eff;
}

.sub-nav-item--active .sub-nav-icon,
.sub-nav-item--active .sub-nav-arrow {
  color: #2563eb;
}

@media (max-width: 820px) {
  .sidebar {
    min-height: auto;
    grid-template-columns: auto auto minmax(0, 1fr);
    grid-template-rows: auto;
    align-items: center;
    padding: 10px 12px;
    border-top: 1px solid #dce3ee;
    border-right: 0;
    overflow: hidden;
  }

  .brand,
  .quick-search,
  .nav-item {
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

  .nav-group {
    width: auto;
  }

  .collapsed-sub-nav-popover {
    display: none;
  }

  .nav-label,
  .brand-copy {
    display: none;
  }
}
</style>
