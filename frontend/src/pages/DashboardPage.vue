<template>
  <PageLayout title="今日总览" subtitle="本地采集数据与工作状态概览">
    <div class="flex h-full min-h-0 min-w-0 flex-col gap-4 overflow-hidden">
      <div class="grid shrink-0 grid-cols-5 gap-4">
        <StatCard title="今日活跃时间" :value="summary.metrics.active_time" :icon-component="Clock" />
        <StatCard title="应用记录" :value="summary.metrics.app_sessions" unit="条" :icon-component="Grid" />
        <StatCard title="剪贴板" :value="summary.metrics.clipboard" unit="条" :icon-component="CopyDocument" tone="purple" />
        <StatCard title="浏览记录" :value="summary.metrics.browser" unit="条" :icon-component="Monitor" tone="green" />
        <StatCard title="AI 提问" :value="summary.metrics.ai_prompts" unit="条" icon="AI" tone="orange" />
      </div>

      <div v-loading="dashboard.loading" class="grid min-h-0 min-w-0 flex-1 grid-cols-2 grid-rows-[minmax(0,1fr)_minmax(0,1fr)] gap-4">
        <ChartCard title="Top 应用（按活跃时长）">
          <template #actions>
            <el-select model-value="active" size="small" style="width: 118px">
              <el-option label="按活跃时长" value="active" />
            </el-select>
          </template>
          <div v-if="summary.top_apps.length" class="h-full min-h-0 overflow-auto pr-1">
            <div v-for="item in summary.top_apps" :key="item.name" class="mb-4 flex items-center gap-3">
              <div class="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-blue-50 text-xs font-black text-blue-600">
                {{ item.name.slice(0, 1).toUpperCase() }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="mb-1 flex items-center justify-between gap-3">
                  <span class="truncate text-sm font-bold text-slate-700">{{ item.name }}</span>
                  <span class="shrink-0 text-sm font-bold text-slate-500">{{ secondsText(item.seconds) }}</span>
                </div>
                <el-progress :percentage="topPercent(item.seconds)" :show-text="false" :stroke-width="9" />
              </div>
            </div>
          </div>
          <EmptyState v-else title="暂无应用记录" description="运行采集服务后会显示今日应用使用分布。" />
        </ChartCard>

        <ChartCard title="今日时间分布（活跃 / 空闲）">
          <div class="flex h-full min-h-0 flex-col gap-3">
            <div class="time-chart min-h-0 flex-1">
              <div class="time-bars">
                <div v-for="slot in summary.time_distribution" :key="slot.label" class="hour-slot" :title="`${slot.label} ${secondsText(slot.active)}`">
                  <div class="hour-track">
                    <div class="hour-fill" :style="{ height: `${slotPercent(slot.active)}%` }"></div>
                  </div>
                </div>
              </div>
              <div class="grid shrink-0 grid-cols-5 pt-2 text-xs font-semibold text-slate-400">
                <span>00:00</span>
                <span>06:00</span>
                <span>12:00</span>
                <span>18:00</span>
                <span class="text-right">24:00</span>
              </div>
            </div>
            <div class="grid shrink-0 grid-cols-3 gap-3">
              <div class="time-metric-card">
                <el-icon class="text-blue-600" :size="18"><Clock /></el-icon>
                <div class="min-w-0">
                  <div class="truncate text-xs font-bold text-slate-500">活跃时长</div>
                  <div class="truncate text-lg font-black text-slate-900">{{ summary.metrics.active_time }}</div>
                </div>
              </div>
              <div class="time-metric-card">
                <el-icon class="text-slate-500" :size="18"><Timer /></el-icon>
                <div class="min-w-0">
                  <div class="truncate text-xs font-bold text-slate-500">空闲时长</div>
                  <div class="truncate text-lg font-black text-slate-900">{{ idleTimeText }}</div>
                </div>
              </div>
              <div class="time-metric-card">
                <el-icon class="text-emerald-600" :size="18"><PieChart /></el-icon>
                <div class="min-w-0">
                  <div class="truncate text-xs font-bold text-slate-500">活跃比例</div>
                  <div class="truncate text-lg font-black text-slate-900">{{ activeRatioText }}</div>
                </div>
              </div>
            </div>
          </div>
        </ChartCard>

        <ChartCard title="最近活动">
          <template #actions>
            <RouterLink to="/data" class="text-sm font-bold text-blue-600">查看全部</RouterLink>
          </template>
          <div v-if="summary.recent_activities.length" class="h-full min-h-0 overflow-auto">
            <div v-for="item in summary.recent_activities" :key="`${item.time}-${item.title}`" class="flex min-w-0 items-center gap-3 border-b border-slate-100 py-3 last:border-0">
              <div class="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-50 font-bold text-emerald-600">{{ item.source.slice(0, 1) || 'D' }}</div>
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-bold text-slate-800">{{ item.title || item.source }}</div>
                <div class="truncate text-xs text-slate-500">{{ item.source }}</div>
              </div>
              <el-tag effect="light" round>{{ item.time }}</el-tag>
            </div>
          </div>
          <EmptyState v-else title="暂无最近活动" />
        </ChartCard>

        <ChartCard title="本周趋势">
          <div ref="trendRef" class="h-full min-h-0"></div>
        </ChartCard>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import * as echarts from 'echarts'
import { Clock, CopyDocument, Grid, Monitor, PieChart, Timer } from '@element-plus/icons-vue'
import ChartCard from '../components/ChartCard.vue'
import EmptyState from '../components/EmptyState.vue'
import StatCard from '../components/StatCard.vue'
import PageLayout from '../layouts/PageLayout.vue'
import { useAppStore } from '../stores/app'
import { useDashboardStore } from '../stores/dashboard'
import type { DashboardSummary } from '../api/types'

const app = useAppStore()
const dashboard = useDashboardStore()
const trendRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null

const emptySummary: DashboardSummary = {
  date: app.currentDate,
  metrics: { active_time: '0m', total_time: '0m', app_sessions: 0, clipboard: 0, browser: 0, ai_prompts: 0 },
  top_apps: [],
  time_distribution: Array.from({ length: 24 }, (_, index) => ({ label: `${String(index).padStart(2, '0')}:00`, active: 0 })),
  recent_activities: [],
  weekly_trend: []
}

const summary = computed(() => dashboard.summary || emptySummary)
const maxTop = computed(() => Math.max(1, ...summary.value.top_apps.map((item) => item.seconds)))
const maxSlot = computed(() => Math.max(1, ...summary.value.time_distribution.map((item) => item.active)))
const activeMetricSeconds = computed(() => parseDurationText(summary.value.metrics.active_time))
const totalMetricSeconds = computed(() => parseDurationText(summary.value.metrics.total_time))
const idleMetricSeconds = computed(() => Math.max(0, totalMetricSeconds.value - activeMetricSeconds.value))
const idleTimeText = computed(() => secondsText(idleMetricSeconds.value))
const activeRatioText = computed(() => totalMetricSeconds.value > 0 ? `${Math.round((activeMetricSeconds.value / totalMetricSeconds.value) * 100)}%` : '0%')

function topPercent(value: number) {
  return Math.max(2, Math.round((value / maxTop.value) * 100))
}

function slotPercent(active: number) {
  return active ? Math.max(8, Math.round((active / maxSlot.value) * 100)) : 0
}

function secondsText(value: number) {
  if (value >= 3600) return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`
  if (value > 0 && value < 60) return '<1m'
  return `${Math.floor(value / 60)}m`
}

function parseDurationText(value: string | number) {
  if (typeof value === 'number') return value
  const text = String(value || '')
  const hours = Number(text.match(/(\d+)\s*h/)?.[1] || 0)
  const minutes = Number(text.match(/(\d+)\s*m/)?.[1] || 0)
  const seconds = Number(text.match(/(\d+)\s*s/)?.[1] || 0)
  if (!hours && !minutes && !seconds) return Number(text) || 0
  return hours * 3600 + minutes * 60 + seconds
}

async function load() {
  await dashboard.load(app.currentDate)
  await nextTick()
  renderTrend()
}

function renderTrend() {
  if (!trendRef.value) return
  trendChart = trendChart || echarts.init(trendRef.value)
  trendChart.resize()
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 18, left: 12, right: 18, bottom: 12, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: summary.value.weekly_trend.map((item) => item.date.slice(5)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dbe3ef' } },
      axisLabel: { color: '#94a3b8', fontWeight: 700 }
    },
    yAxis: {
      type: 'value',
      scale: true,
      minInterval: 1,
      splitNumber: 3,
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#e8eef7' } },
      axisLabel: { color: '#94a3b8', fontWeight: 700, margin: 10 }
    },
    series: [{
      type: 'line',
      smooth: true,
      symbolSize: 7,
      data: summary.value.weekly_trend.map((item) => item.count),
      lineStyle: { width: 3, color: '#2563eb' },
      itemStyle: { color: '#2563eb' },
      areaStyle: { color: 'rgba(37, 99, 235, .08)' }
    }]
  })
}

onMounted(load)
watch(() => app.currentDate, load)
</script>

<style scoped>
.time-chart {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.time-bars {
  display: grid;
  min-height: 0;
  flex: 1;
  grid-template-columns: repeat(24, minmax(0, 1fr));
  gap: 8px;
  overflow: hidden;
}

.hour-slot {
  display: flex;
  min-width: 0;
  align-items: flex-end;
}

.hour-track {
  position: relative;
  width: 100%;
  max-width: 18px;
  min-width: 7px;
  height: 100%;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 6px 6px 2px 2px;
  background: #e5ebf4;
}

.hour-fill {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  min-height: 0;
  border-radius: 6px 6px 2px 2px;
  background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
  transition: height .2s ease;
}

.time-metric-card {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
  padding: 10px 12px;
}
</style>
