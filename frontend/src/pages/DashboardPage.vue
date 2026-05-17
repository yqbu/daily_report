<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-black tracking-tight">今日总览</h2>
        <p class="mt-2 text-slate-500">本地采集数据与工作状态概览</p>
      </div>
      <DateRangeFilter v-model="app.currentDate" @refresh="load" />
    </div>

    <LoadingState v-if="dashboard.loading" />
    <div v-else class="space-y-6">
      <div class="grid grid-cols-5 gap-4">
        <StatCard title="活跃时间" :value="summary.metrics.active_time" icon="◷" />
        <StatCard title="应用记录" :value="summary.metrics.app_sessions" unit="条" icon="▦" />
        <StatCard title="剪贴板" :value="summary.metrics.clipboard" unit="条" icon="▣" tone="purple" />
        <StatCard title="浏览记录" :value="summary.metrics.browser" unit="条" icon="◎" tone="green" />
        <StatCard title="AI 提问" :value="summary.metrics.ai_prompts" unit="条" icon="AI" tone="orange" />
      </div>

      <div class="grid grid-cols-2 gap-5">
        <ChartCard title="Top 应用" subtitle="按活跃时长排序">
          <div v-if="summary.top_apps.length" ref="topAppsRef" class="h-72"></div>
          <EmptyState v-else title="暂无应用记录" description="运行采集服务后会显示今日应用使用分布。" />
        </ChartCard>

        <ChartCard title="今日时间分布" subtitle="按小时聚合活跃记录">
          <div class="flex h-72 items-end gap-1.5 px-1 pb-7 pt-6">
            <div v-for="slot in summary.time_distribution" :key="slot.label" class="group flex flex-1 flex-col items-center gap-2">
              <div class="w-full rounded-full bg-slate-100">
                <div class="mx-auto w-2.5 rounded-full bg-blue-600 transition-all" :style="{ height: `${slotHeight(slot.active)}px` }"></div>
              </div>
              <span v-if="slot.label.endsWith('00') && ['00:00', '06:00', '12:00', '18:00'].includes(slot.label)" class="text-[11px] text-slate-400">{{ slot.label.slice(0, 2) }}</span>
            </div>
          </div>
        </ChartCard>
      </div>

      <div class="grid grid-cols-[1.1fr_.9fr] gap-5">
        <ChartCard title="最近活动">
          <div v-if="summary.recent_activities.length" class="divide-y divide-slate-100">
            <div v-for="item in summary.recent_activities" :key="`${item.time}-${item.title}`" class="flex items-center gap-4 py-3">
              <div class="w-14 text-sm font-bold text-slate-500">{{ item.time }}</div>
              <div class="min-w-0 flex-1">
                <div class="truncate font-semibold text-slate-800">{{ item.title || item.source }}</div>
                <div class="text-sm text-slate-500">{{ item.source }}</div>
              </div>
              <StatusBadge label="应用" />
            </div>
          </div>
          <EmptyState v-else title="暂无最近活动" />
        </ChartCard>

        <div class="space-y-5">
          <ChartCard title="快捷入口">
            <div class="grid grid-cols-3 gap-3">
              <RouterLink class="quick-card" to="/data">数据中心<span>查看数据</span></RouterLink>
              <RouterLink class="quick-card green" to="/workbench">日报工作台<span>生成日报</span></RouterLink>
              <RouterLink class="quick-card purple" to="/settings">设置<span>应用偏好</span></RouterLink>
            </div>
          </ChartCard>
          <ChartCard title="本周趋势">
            <div ref="trendRef" class="h-52"></div>
          </ChartCard>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import * as echarts from 'echarts'
import ChartCard from '../components/ChartCard.vue'
import DateRangeFilter from '../components/DateRangeFilter.vue'
import EmptyState from '../components/EmptyState.vue'
import LoadingState from '../components/LoadingState.vue'
import StatCard from '../components/StatCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAppStore } from '../stores/app'
import { useDashboardStore } from '../stores/dashboard'
import type { DashboardSummary } from '../api/types'

const app = useAppStore()
const dashboard = useDashboardStore()
const topAppsRef = ref<HTMLElement | null>(null)
const trendRef = ref<HTMLElement | null>(null)
let topChart: echarts.ECharts | null = null
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
const maxSlot = computed(() => Math.max(1, ...summary.value.time_distribution.map((item) => item.active)))

function slotHeight(active: number) {
  return Math.max(14, Math.round((active / maxSlot.value) * 160))
}

async function load() {
  await dashboard.load(app.currentDate)
  await nextTick()
  renderCharts()
}

function renderCharts() {
  if (topAppsRef.value && summary.value.top_apps.length) {
    topChart = topChart || echarts.init(topAppsRef.value)
    topChart.setOption({
      grid: { top: 8, left: 80, right: 24, bottom: 24 },
      xAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#eef2f7' } } },
      yAxis: { type: 'category', data: summary.value.top_apps.map((item) => item.name).reverse(), axisLabel: { color: '#475569' } },
      series: [{ type: 'bar', data: summary.value.top_apps.map((item) => item.seconds).reverse(), itemStyle: { color: '#2563eb', borderRadius: 8 }, barWidth: 12 }]
    })
  }
  if (trendRef.value) {
    trendChart = trendChart || echarts.init(trendRef.value)
    trendChart.setOption({
      grid: { top: 18, left: 28, right: 18, bottom: 28 },
      xAxis: { type: 'category', data: summary.value.weekly_trend.map((item) => item.date.slice(5)), axisLabel: { color: '#94a3b8' }, axisTick: { show: false } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#eef2f7' } } },
      series: [{ type: 'line', smooth: true, data: summary.value.weekly_trend.map((item) => item.count), symbolSize: 7, lineStyle: { width: 3, color: '#2563eb' }, itemStyle: { color: '#2563eb' }, areaStyle: { color: 'rgba(37,99,235,.08)' } }]
    })
  }
}

onMounted(load)
watch(() => app.currentDate, load)
</script>

<style scoped>
.quick-card {
  display: flex;
  min-height: 88px;
  flex-direction: column;
  justify-content: center;
  border-radius: 16px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  padding: 16px;
  font-weight: 800;
  color: #1d4ed8;
}

.quick-card span {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.quick-card.green {
  border-color: #c7f0d8;
  background: #ecfdf5;
  color: #059669;
}

.quick-card.purple {
  border-color: #ddd6fe;
  background: #f5f3ff;
  color: #7c3aed;
}
</style>
