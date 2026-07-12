<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Calendar,
  Collection,
  CopyDocument,
  Link,
  Monitor,
  Refresh,
  Stopwatch
} from '@element-plus/icons-vue'

import type { OverviewPayload, SourceType } from '../api/types'
import { useTodayOverviewData } from '../composables/useTodayOverviewData'
import DateRangePicker from '../components/DateRangePicker.vue'
import { formatMonthDay, parseIsoDate } from '../utils/date'
import { formatDuration, formatTime, getPercent } from '../utils/format'
import { buildDonutBackground, iconSource } from '../utils/todayOverview'

type Tone = 'blue' | 'green' | 'orange' | 'purple' | 'slate'

interface MetricItem {
  id: string
  title: string
  value: string | number
  helper: string
  icon: unknown
  tone: Tone
}

interface TopAppItem {
  id: string
  name: string
  seconds: number
  percent: number
  color: string
  iconSrc: string
  initial: string
  category: string
  sessionCount: number
}

interface DistributionItem {
  id: string
  label: string
  value: number
  percent: number
  color: string
}

interface HourPoint {
  hour: number
  label: string
  activeSec: number
  totalSec: number
}

interface TimeDistributionPoint {
  id: string
  label: string
  axisLabel: string
  activeSec: number
  totalSec: number
}

interface RecentActivityItem {
  id: string
  title: string
  subtitle: string
  time: string
  sourceType: SourceType
}

const sourceMeta: Record<SourceType, { label: string; color: string; tone: Tone }> = {
  app: { label: '前台应用', color: '#2563eb', tone: 'blue' },
  browser: { label: '浏览器', color: '#10b981', tone: 'green' },
  clipboard: { label: '剪贴板', color: '#f59e0b', tone: 'orange' },
  ai_prompt: { label: '浏览器', color: '#10b981', tone: 'green' },
  browser_event: { label: '浏览器', color: '#10b981', tone: 'green' }
}

const categoryPalette = ['#2563eb', '#10b981', '#f59e0b', '#7c3aed', '#6366f1', '#98a2b3']
const expectedCategories = ['开发编程', '资料调研', 'AI 能力', '文档撰写', '沟通协作', '其他']
const {
  dateRange,
  overviewDays,
  recentEvents,
  appProfiles,
  loading,
  selectedDates,
  loadOverview,
  handleDateRangeChange
} = useTodayOverviewData()

const rangeLabel = computed(() => {
  const [start, end] = dateRange.value
  return `${formatMonthDay(start)} - ${formatMonthDay(end)}`
})
const aggregated = computed(() => aggregateOverview(overviewDays.value))
const activeRate = computed(() => getPercent(aggregated.value.activeSec, aggregated.value.totalSec))
const browserMetricHelper = computed(() => {
  const counts = aggregated.value.browserRecordTypes
  const parts = [
    ['搜索', counts.search ?? 0],
    ['AI 提问', counts.ai_prompt ?? 0],
    ['访问', (counts.history_visit ?? 0) + (counts.page_view ?? 0)]
  ].filter(([, value]) => Number(value) > 0)
  return parts.length ? parts.map(([label, value]) => `${label}${value}`).join(' / ') : '网页、搜索与 AI 线索'
})
const reportStatusText = computed(() => {
  const total = overviewDays.value.length
  if (total === 0) return '日报：未生成'

  const generated = overviewDays.value.filter((item) => isReportGenerated(item.report_status)).length
  if (total === 1) return generated > 0 ? '日报：已生成' : '日报：未生成'
  return `日报：${generated}/${total} 天已生成`
})
const metrics = computed<MetricItem[]>(() => [
  {
    id: 'active',
    title: '活跃时间',
    value: formatDuration(aggregated.value.activeSec),
    // helper: `总时长 ${formatDuration(aggregated.value.totalSec)} · 活跃率 ${activeRate.value.toFixed(0)}%`,
    helper: `总时长 ${formatDuration(aggregated.value.totalSec)}`,
    icon: Stopwatch,
    tone: 'blue'
  },
  {
    id: 'apps',
    title: '应用记录',
    value: aggregated.value.appSessions,
    helper: `${topApps.value.length} 个主要应用`,
    icon: Monitor,
    tone: 'slate'
  },
  {
    id: 'clipboard',
    title: '剪贴板',
    value: aggregated.value.clipboard,
    helper: '本地剪贴板素材',
    icon: CopyDocument,
    tone: 'orange'
  },
  {
    id: 'browser',
    title: '浏览器',
    value: aggregated.value.browser,
    helper: browserMetricHelper.value,
    icon: Link,
    tone: 'green'
  }
])
const topApps = computed<TopAppItem[]>(() => {
  const total = Math.max(aggregated.value.activeSec, 1)
  return aggregated.value.topApps.slice(0, 6).map((item, index) => ({
    id: item.id,
    name: item.name,
    seconds: item.seconds,
    percent: getPercent(item.seconds, total),
    color: item.color || categoryPalette[index % categoryPalette.length],
    iconSrc: item.iconSrc,
    initial: item.name.trim().slice(0, 1).toUpperCase() || 'A',
    category: item.category,
    sessionCount: item.sessionCount
  }))
})
const categoryDistribution = computed<DistributionItem[]>(() => {
  const total = Math.max(aggregated.value.categoryTotal, 1)
  return expectedCategories.map((category, index) => ({
    id: category,
    label: category,
    value: aggregated.value.categories[category] ?? 0,
    percent: getPercent(aggregated.value.categories[category] ?? 0, total),
    color: categoryPalette[index]
  }))
})
const categoryDonutStyle = computed(() => ({ background: buildDonutBackground(categoryDistribution.value) }))
const hourlyPoints = computed<HourPoint[]>(() => {
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    label: `${String(hour).padStart(2, '0')}:00`,
    activeSec: aggregated.value.hourly[hour]?.activeSec ?? 0,
    totalSec: aggregated.value.hourly[hour]?.totalSec ?? 0
  }))
})
const isSingleDayRange = computed(() => selectedDates.value.length <= 1)
const timeDistributionModeLabel = computed(() => (isSingleDayRange.value ? '按小时统计' : '按日统计'))
const timeDistributionPoints = computed<TimeDistributionPoint[]>(() => {
  if (isSingleDayRange.value) {
    return hourlyPoints.value.map((point) => ({
      id: `hour-${point.hour}`,
      label: point.label,
      axisLabel: point.label,
      activeSec: point.activeSec,
      totalSec: point.totalSec
    }))
  }

  const dayMap = new Map(overviewDays.value.map((day) => [day.date, day]))
  return selectedDates.value.map((date) => {
    const day = dayMap.get(date)
    const parsedDate = parseIsoDate(date)
    return {
      id: `day-${date}`,
      label: formatMonthDay(parsedDate),
      axisLabel: formatMonthDay(parsedDate),
      activeSec: day?.active_time_sec ?? 0,
      totalSec: Math.max(day?.total_time_sec ?? 0, day?.active_time_sec ?? 0)
    }
  })
})
const timeDistributionAxis = computed(() => {
  if (isSingleDayRange.value) {
    return ['00:00', '06:00', '12:00', '18:00', '24:00']
  }

  const points = timeDistributionPoints.value
  if (points.length <= 1) return points.map((point) => point.axisLabel)
  if (points.length <= 7) return points.map((point) => point.axisLabel)

  const middle = points[Math.floor((points.length - 1) / 2)]
  return [points[0].axisLabel, middle.axisLabel, points[points.length - 1].axisLabel]
})
const timeDistributionGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(timeDistributionPoints.value.length, 1)}, minmax(5px, 1fr))`
}))
const maxTimeDistributionSec = computed(() =>
  Math.max(...timeDistributionPoints.value.map((item) => item.totalSec || item.activeSec), 1)
)
const idleSec = computed(() => Math.max(0, aggregated.value.totalSec - aggregated.value.activeSec))
const recentActivities = computed<RecentActivityItem[]>(() =>
  [...recentEvents.value]
    .sort((a, b) => b.start_time.localeCompare(a.start_time))
    .slice(0, 4)
    .map((item) => ({
      id: item.event_id,
      title: item.title || item.content_preview || '未命名活动',
      subtitle: item.subtitle || sourceMeta[item.source_type].label,
      time: formatTime(item.start_time),
      sourceType: item.source_type
    }))
)

function aggregateOverview(days: OverviewPayload[]) {
  const profileIconByKey = new Map(appProfiles.value.map((profile) => [profile.app_key, iconSource(profile)]))
  const appMap = new Map<
    string,
    { id: string; name: string; seconds: number; color: string; iconSrc: string; category: string; sessionCount: number }
  >()
  const categories: Record<string, number> = {}
  const hourly = Array.from({ length: 24 }, () => ({ activeSec: 0, totalSec: 0 }))

  let activeSec = 0
  let totalSec = 0
  let appSessions = 0
  let browser = 0
  let clipboard = 0
  let aiPrompts = 0
  let browserEvents = 0
  const browserRecordTypes: Record<string, number> = {}

  for (const day of days) {
    activeSec += day.active_time_sec ?? 0
    totalSec += day.total_time_sec ?? 0
    appSessions += day.app_session_count ?? 0
    browser += day.browser_count ?? 0
    clipboard += day.clipboard_count ?? 0
    aiPrompts += day.ai_prompt_count ?? 0
    browserEvents += day.browser_event_count ?? 0
    for (const [recordType, count] of Object.entries(day.browser_record_type_counts ?? {})) {
      browserRecordTypes[recordType] = (browserRecordTypes[recordType] ?? 0) + Number(count || 0)
    }

    for (const app of day.top_apps ?? []) {
      const id = app.app_key || app.name || app.app_name || 'unknown'
      const existing = appMap.get(id) ?? {
        id,
        name: app.name || app.app_name || '未知应用',
        seconds: 0,
        color: app.color || '',
        iconSrc: profileIconByKey.get(id) || '',
        category: app.category || '',
        sessionCount: 0
      }
      existing.seconds += app.seconds ?? 0
      existing.sessionCount += app.session_count ?? 0
      if (!existing.color && app.color) existing.color = app.color
      if (!existing.category && app.category) existing.category = app.category
      if (!existing.iconSrc) existing.iconSrc = profileIconByKey.get(id) || ''
      appMap.set(id, existing)
    }

    for (const item of day.category_distribution ?? []) {
      const category = expectedCategories.includes(item.category) ? item.category : '其他'
      categories[category] = (categories[category] ?? 0) + item.count
    }

    for (const point of day.hourly_activity ?? []) {
      if (point.hour >= 0 && point.hour < hourly.length) {
        const activeSec = point.active_sec ?? 0
        const totalSec = point.total_sec ?? activeSec
        hourly[point.hour].activeSec += activeSec
        hourly[point.hour].totalSec += Math.max(totalSec, activeSec)
      }
    }
  }

  const topApps = [...appMap.values()].sort((a, b) => b.seconds - a.seconds)
  const categoryTotal = Object.values(categories).reduce((sum, value) => sum + value, 0)

  return {
    activeSec,
    totalSec,
    appSessions,
    browser,
    clipboard,
    aiPrompts,
    browserEvents,
    browserRecordTypes,
    topApps,
    categories,
    categoryTotal,
    hourly
  }
}

function isReportGenerated(status: string): boolean {
  const text = String(status || '').toLowerCase()
  return text.includes('已生成') || text.includes('generated')
}

function sourceIcon(sourceType: SourceType): unknown {
  if (sourceType === 'browser' || sourceType === 'browser_event') return Link
  if (sourceType === 'clipboard') return CopyDocument
  if (sourceType === 'ai_prompt') return Link
  return Monitor
}

</script>

<template>
  <main class="today-overview" :class="{ 'today-overview--loading': loading }">
    <header class="overview-topbar">
      <div class="title-block">
        <span class="workspace-label">Daily Report</span>
        <h1 class="page-title">今日总览</h1>
      </div>

      <div class="top-actions">
        <DateRangePicker
          v-model="dateRange"
          class="date-picker"
          @change="handleDateRangeChange"
        />

        <button class="top-button" type="button" :disabled="loading" title="刷新当前日期范围数据" @click="loadOverview">
          <Refresh class="action-icon" :class="{ 'action-icon--spin': loading }" />
          <span>刷新</span>
        </button>

        <div class="report-pill" title="日报生成状态">
          <Collection class="action-icon" />
          <span>{{ reportStatusText }}</span>
          <RouterLink class="report-link" to="/reports">前往生成</RouterLink>
        </div>
      </div>
    </header>

    <section class="metrics-grid" aria-label="今日关键指标">
      <section v-for="metric in metrics" :key="metric.id" class="metric-card" :class="`metric-card--${metric.tone}`">
        <span class="metric-icon">
          <component :is="metric.icon" />
        </span>
        <span class="metric-copy">
          <span class="metric-title">{{ metric.title }}</span>
          <strong>{{ metric.value }}</strong>
          <span class="metric-helper">{{ metric.helper }}</span>
        </span>
      </section>
    </section>

    <section class="overview-dashboard-grid">
      <section class="overview-card top-app-card">
        <header class="card-header">
          <h2>Top 应用</h2>
          <RouterLink class="header-link" to="/apps">查看全部应用</RouterLink>
        </header>

        <div v-if="topApps.length === 0" class="empty-state">暂无应用数据</div>
        <ul v-else class="top-app-list">
          <li v-for="(app, index) in topApps" :key="app.id" class="top-app-row">
            <span class="app-avatar" :class="{ 'app-avatar--has-icon': app.iconSrc }" :style="{ color: app.color }">
              <img v-if="app.iconSrc" class="app-icon" :src="app.iconSrc" alt="" />
              <span v-else>{{ app.initial }}</span>
            </span>
            <span class="app-main">
              <span class="app-line">
                <strong>{{ app.name }}</strong>
                <time>{{ formatDuration(app.seconds) }}</time>
              </span>
              <span class="app-meta">
                <span>{{ app.category || '未分类' }}</span>
                <span>{{ app.sessionCount }} 条记录</span>
                <span>{{ app.percent.toFixed(1) }}%</span>
              </span>
              <span class="app-track">
                <span class="app-progress" :style="{ width: `${Math.max(app.percent, 2)}%` }"></span>
              </span>
            </span>
            <span class="app-rank">{{ index + 1 }}</span>
          </li>
        </ul>
      </section>

      <section class="overview-card recent-card">
        <header class="card-header">
          <h2>最近活动</h2>
          <RouterLink class="header-link" to="/data">查看全部</RouterLink>
        </header>

        <div v-if="recentActivities.length === 0" class="empty-state">暂无最近活动</div>
        <ul v-else class="activity-list">
          <li v-for="item in recentActivities" :key="item.id" class="activity-row">
            <span class="activity-icon" :class="`activity-icon--${sourceMeta[item.sourceType].tone}`">
              <component :is="sourceIcon(item.sourceType)" />
            </span>
            <span class="activity-copy">
              <strong>{{ item.title }}</strong>
              <span>{{ item.subtitle }}</span>
            </span>
            <time>{{ item.time }}</time>
          </li>
        </ul>
      </section>

      <section class="overview-card category-card">
        <header class="card-header">
          <h2>分类分析</h2>
          <RouterLink class="header-link" to="/apps">管理分类</RouterLink>
        </header>

        <div v-if="aggregated.categoryTotal === 0" class="empty-state">暂无分类数据</div>
        <div v-else class="distribution-layout">
          <div class="donut" :style="categoryDonutStyle">
            <div class="donut-inner">
              <strong>{{ aggregated.categoryTotal }}</strong>
              <span>已分类</span>
            </div>
          </div>
          <ul class="distribution-list">
            <li v-for="item in categoryDistribution" :key="item.id">
              <span class="swatch" :style="{ backgroundColor: item.color }"></span>
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <em>{{ item.percent.toFixed(1) }}%</em>
            </li>
          </ul>
        </div>
      </section>

      <section class="overview-card time-card">
        <header class="card-header">
          <span class="card-title-group">
            <h2>时间分布（活跃 / 统计）</h2>
            <em>{{ timeDistributionModeLabel }}</em>
          </span>
          <span class="time-legend">
            <span><i class="legend-dot legend-dot--active"></i>活跃</span>
            <span><i class="legend-dot legend-dot--tracked"></i>统计</span>
<!--            <span><i class="legend-dot"></i>空闲</span>-->
          </span>
        </header>

        <div class="time-bars" :style="timeDistributionGridStyle">
          <span
            v-for="point in timeDistributionPoints"
            :key="point.id"
            class="time-bar"
            :class="{ 'time-bar--tracked': point.totalSec > 0, 'time-bar--active': point.activeSec > 0 }"
            :title="`${point.label} 统计 ${formatDuration(point.totalSec)} / 活跃 ${formatDuration(point.activeSec)}`"
          >
            <span
              class="time-bar-stat"
              :style="{ height: point.totalSec > 0 ? `${Math.max(8, (point.totalSec / maxTimeDistributionSec) * 100)}%` : '0%' }"
            ></span>
            <span
              class="time-bar-fill"
              :style="{ height: point.activeSec > 0 ? `${Math.max(8, (point.activeSec / maxTimeDistributionSec) * 100)}%` : '0%' }"
            ></span>
          </span>
        </div>

        <div class="time-axis">
          <span v-for="label in timeDistributionAxis" :key="label">{{ label }}</span>
        </div>

        <div class="time-summary">
          <span class="summary-card summary-card--active">
            <Stopwatch />
            <span>
              <em>活跃时长</em>
              <strong>{{ formatDuration(aggregated.activeSec) }}</strong>
            </span>
          </span>
          <span class="summary-card">
            <Calendar />
            <span>
              <em>空闲时长</em>
              <strong>{{ formatDuration(idleSec) }}</strong>
            </span>
          </span>
          <span class="summary-card summary-card--rate">
            <Monitor />
            <span>
              <em>活跃比例</em>
              <strong>{{ activeRate.toFixed(0) }}%</strong>
            </span>
          </span>
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.today-overview {
  --overview-text: #172033;
  --overview-muted: #667085;
  --overview-subtle: #98a2b3;
  --overview-border: #dce3ee;
  --overview-soft-border: #e6ebf3;
  --overview-blue: #409eff;
  --overview-green: #67c23a;
  --overview-orange: #e6a23c;
  --overview-purple: #f56c6c;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  align-content: stretch;
  gap: 12px;
  overflow-x: hidden;
  overflow-y: auto;
  color: var(--overview-text);
  background: #fbfcfd;
}

.overview-topbar,
.metric-card,
.overview-card {
  border: 1px solid var(--overview-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
}

.metric-card,
.overview-card {
  animation: overview-card-enter 520ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.metric-card:nth-child(2),
.recent-card {
  animation-delay: 35ms;
}

.metric-card:nth-child(3),
.category-card {
  animation-delay: 70ms;
}

.metric-card:nth-child(4),
.time-card {
  animation-delay: 105ms;
}

.metric-card:nth-child(5) {
  animation-delay: 140ms;
}

.overview-topbar {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
}

.title-block {
  min-width: 0;
}

.workspace-label {
  display: block;
  color: var(--overview-muted);
  font-size: 12px;
  line-height: 1.2;
}

.page-title {
  margin: 4px 0 0;
  color: var(--overview-text);
  font-size: 22px;
  font-weight: 720;
  line-height: 1.15;
  letter-spacing: 0;
}

.top-actions {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.report-pill,
.top-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid var(--overview-border);
  border-radius: 8px;
  color: #526179;
  background: #ffffff;
  font-size: 13px;
  white-space: nowrap;
}

.report-pill {
  background: #ffffff;
}

.report-link,
.header-link {
  color: var(--overview-blue);
  font-weight: 760;
  text-decoration: none;
}

.report-link:hover,
.header-link:hover {
  color: #1d4ed8;
}

.top-button {
  cursor: pointer;
}

.top-button:hover {
  color: var(--overview-blue);
  border-color: #c9dcff;
  background: #eff6ff;
}

.top-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.action-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.action-icon--spin {
  animation: overview-spin 900ms linear infinite;
}

.date-picker {
  width: 274px;
}

.today-overview :deep(.el-date-editor.el-input__wrapper) {
  height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 0 0 1px var(--overview-border) inset;
}

.today-overview :deep(.el-date-editor.el-input__wrapper:hover),
.today-overview :deep(.el-date-editor.el-input__wrapper.is-active) {
  box-shadow: 0 0 0 1px #c9dcff inset;
}

.today-overview :deep(.el-date-editor .el-range-input) {
  color: var(--overview-text);
  font-size: 13px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}

.metric-card {
  min-width: 0;
  min-height: 94px;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
}

.metric-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
}

.metric-icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.metric-card--blue .metric-icon {
  color: var(--overview-blue);
  background: #eff6ff;
}

.metric-card--green .metric-icon {
  color: var(--overview-green);
  background: #ecfdf5;
}

.metric-card--orange .metric-icon {
  color: var(--overview-orange);
  background: #fffbeb;
}

.metric-card--purple .metric-icon {
  color: var(--overview-purple);
  background: #f5f3ff;
}

.metric-card--slate .metric-icon {
  color: #526179;
  background: #f8fafc;
}

.metric-copy {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.metric-title,
.metric-helper {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-title {
  color: #526179;
  font-size: 13px;
  font-weight: 700;
}

.metric-copy strong {
  color: var(--overview-text);
  font-size: 22px;
  font-weight: 780;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.metric-helper {
  color: var(--overview-subtle);
  font-size: 12px;
  font-weight: 620;
}

.overview-dashboard-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  grid-template-rows: minmax(220px, 1fr) minmax(260px, 1.15fr);
  gap: 12px;
}

.overview-card {
  min-width: 0;
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 13px;
  padding: 15px 16px;
  overflow: hidden;
}

.top-app-card {
  grid-row: 1 / span 2;
}

.recent-card {
  grid-column: 2;
  grid-row: 1;
}

.category-card {
  grid-column: 3;
  grid-row: 1;
}

.time-card {
  grid-column: 2 / span 2;
  grid-row: 2;
}

.card-header {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-header h2 {
  margin: 0;
  color: var(--overview-text);
  font-size: 15px;
  font-weight: 780;
  line-height: 1.2;
}

.card-title-group {
  min-width: 0;
  display: inline-grid;
  gap: 4px;
}

.card-title-group em {
  color: var(--overview-muted);
  font-size: 12px;
  font-style: normal;
  font-weight: 650;
}

.header-link {
  flex: 0 0 auto;
  font-size: 13px;
}

.empty-state {
  min-height: 156px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--overview-border);
  border-radius: 8px;
  color: var(--overview-muted);
  background: #f8fafc;
  font-size: 13px;
  font-weight: 650;
}

.top-app-list,
.distribution-list,
.activity-list {
  display: grid;
  gap: 9px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.top-app-row {
  min-width: 0;
  min-height: 74px;
  padding: 7px 0;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 22px;
  align-items: center;
  gap: 12px;
  animation: overview-list-enter 480ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.app-avatar {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: #eff6ff;
  font-size: 16px;
  font-weight: 800;
  overflow: hidden;
}

.app-avatar--has-icon {
  background: #ffffff;
  box-shadow: inset 0 0 0 1px var(--overview-soft-border);
}

.app-icon {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  object-fit: contain;
}

.app-main {
  min-width: 0;
  display: grid;
  gap: 7px;
}

.app-line {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.app-line strong {
  min-width: 0;
  overflow: hidden;
  color: var(--overview-text);
  font-size: 14px;
  font-weight: 740;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-line time {
  color: #526179;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.app-meta {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--overview-muted);
  font-size: 12px;
  font-weight: 620;
}

.app-meta span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf1f7;
}

.app-progress {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  transform-origin: left center;
  animation: overview-progress-enter 760ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.app-rank {
  color: var(--overview-subtle);
  font-size: 12px;
  font-weight: 760;
  text-align: right;
}

.distribution-layout {
  min-width: 0;
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.donut {
  width: 104px;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background:
    radial-gradient(circle at center, #fff 0 48%, transparent 49%),
    conic-gradient(#2563eb 0 22%, #10b981 22% 76%, #f59e0b 76% 90%, #7c3aed 90% 100%);
  animation: overview-pop-enter 620ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.donut-inner {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 5px;
  border-radius: 999px;
  background: #fff;
}

.donut-inner strong {
  color: var(--overview-text);
  font-size: 18px;
  font-weight: 780;
  line-height: 1;
}

.donut-inner span {
  color: var(--overview-muted);
  font-size: 11px;
  font-weight: 650;
}

.distribution-list li {
  min-width: 0;
  display: grid;
  grid-template-columns: 9px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 6px;
  color: #344054;
  font-size: 12px;
}

.swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

.distribution-list span:nth-child(2) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.distribution-list strong {
  color: var(--overview-text);
  font-variant-numeric: tabular-nums;
}

.distribution-list em {
  min-width: 44px;
  color: var(--overview-muted);
  font-style: normal;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.activity-list {
  gap: 0;
}

.activity-row {
  min-width: 0;
  height: 48px;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--overview-soft-border);
  animation: overview-list-enter 480ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.activity-row:nth-child(2),
.top-app-row:nth-child(2) {
  animation-delay: 35ms;
}

.activity-row:nth-child(3),
.top-app-row:nth-child(3) {
  animation-delay: 70ms;
}

.activity-row:nth-child(4),
.top-app-row:nth-child(4) {
  animation-delay: 105ms;
}

.activity-row:nth-child(5) {
  animation-delay: 140ms;
}

.activity-row:last-child {
  border-bottom: 0;
}

.activity-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 9px;
}

.activity-icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.activity-icon--blue {
  color: var(--overview-blue);
  background: #eff6ff;
}

.activity-icon--green {
  color: var(--overview-green);
  background: #ecfdf5;
}

.activity-icon--orange {
  color: var(--overview-orange);
  background: #fffbeb;
}

.activity-icon--purple {
  color: var(--overview-purple);
  background: #f5f3ff;
}

.activity-copy {
  min-width: 0;
  max-width: 100%;
  display: grid;
  gap: 2px;
  overflow: hidden;
}

.activity-copy strong,
.activity-copy span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-copy strong {
  color: var(--overview-text);
  font-size: 12px;
  font-weight: 740;
}

.activity-copy span,
.activity-row time {
  color: var(--overview-muted);
  font-size: 11px;
  font-weight: 620;
}

.activity-row time {
  padding: 3px 7px;
  border-radius: 999px;
  color: var(--overview-blue);
  background: #eff6ff;
  font-variant-numeric: tabular-nums;
}

.time-legend {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: var(--overview-muted);
  font-size: 12px;
  font-weight: 650;
}

.time-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #dce3ee;
}

.legend-dot--active {
  background: var(--overview-blue);
}

.legend-dot--tracked {
  background: #bfdbfe;
}

.time-bars {
  min-height: 106px;
  display: grid;
  grid-template-columns: repeat(24, minmax(5px, 1fr));
  align-items: end;
  gap: 8px;
  padding: 10px 5px 0;
}

.time-bar {
  position: relative;
  height: 106px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf1f7;
}

.time-bar-stat,
.time-bar-fill {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  width: 100%;
  min-height: 0;
  border-radius: inherit;
  transform-origin: bottom center;
}

.time-bar-stat {
  background: #bfdbfe;
  animation: overview-bar-enter 760ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.time-bar-fill {
  background: var(--overview-blue);
  animation: overview-bar-enter 760ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.time-bar:not(.time-bar--tracked) .time-bar-stat,
.time-bar:not(.time-bar--active) .time-bar-fill {
  background: transparent;
}

.time-axis {
  display: flex;
  justify-content: space-between;
  color: #667085;
  font-size: 12px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.time-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 0;
}

.summary-card {
  min-width: 0;
  min-height: 70px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid var(--overview-border);
  border-radius: 8px;
  background: #ffffff;
}

.summary-card svg {
  width: 22px;
  height: 22px;
  flex: 0 0 auto;
  color: #667085;
}

.summary-card span {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.summary-card em {
  color: var(--overview-muted);
  font-size: 12px;
  font-style: normal;
  font-weight: 650;
}

.summary-card strong {
  color: #526179;
  font-size: 22px;
  font-weight: 780;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.summary-card--active {
  background: linear-gradient(135deg, #ffffff, #eff6ff);
}

.summary-card--active svg,
.summary-card--active strong {
  color: var(--overview-blue);
}

.summary-card--rate {
  background: linear-gradient(135deg, #ffffff, #ecfdf5);
}

.summary-card--rate svg,
.summary-card--rate strong {
  color: var(--overview-green);
}

@keyframes overview-card-enter {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes overview-list-enter {
  from {
    opacity: 0;
    transform: translateX(-6px);
  }

  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes overview-progress-enter {
  from {
    transform: scaleX(0);
  }

  to {
    transform: scaleX(1);
  }
}

@keyframes overview-bar-enter {
  from {
    transform: scaleY(0);
  }

  to {
    transform: scaleY(1);
  }
}

@keyframes overview-pop-enter {
  from {
    opacity: 0;
    transform: scale(0.96);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes overview-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .metric-card,
  .overview-card,
  .activity-row,
  .top-app-row,
  .app-progress,
  .time-bar-stat,
  .time-bar-fill,
  .donut {
    animation: none;
  }
}

@media (max-width: 1440px) {
  .metrics-grid {
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }
}

@media (max-width: 920px) {
  .overview-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .date-picker {
    width: min(100%, 320px);
  }

  .overview-dashboard-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: none;
  }

  .top-app-card,
  .recent-card,
  .category-card,
  .time-card {
    grid-column: auto;
    grid-row: auto;
  }

  .distribution-layout,
  .time-summary {
    grid-template-columns: minmax(0, 1fr);
  }

  .donut {
    justify-self: center;
  }
}
</style>
