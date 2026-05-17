<template>
  <PageLayout title="今日总览" subtitle="本地采集数据与工作状态概览">
    <template #actions>
      <el-button class="glass-button" :icon="Refresh" @click="load">统一风格</el-button>
      <el-button class="glass-button" :icon="Grid">概览卡片</el-button>
      <el-button class="glass-button" :icon="Lightning">快速跳转</el-button>
    </template>

    <div class="flex h-full min-h-0 min-w-0 flex-col gap-4 overflow-hidden">
      <div class="grid shrink-0 grid-cols-5 gap-4">
        <StatCard title="今日活跃时间" :value="summary.metrics.active_time" :icon-component="Clock" />
        <StatCard title="应用记录" :value="summary.metrics.app_sessions" unit="条" :icon-component="Grid" />
        <StatCard title="剪贴板" :value="summary.metrics.clipboard" unit="条" :icon-component="CopyDocument" tone="purple" />
        <StatCard title="浏览记录" :value="summary.metrics.browser" unit="条" :icon-component="Monitor" tone="green" />
        <StatCard title="AI 提问" :value="summary.metrics.ai_prompts" unit="条" icon="AI" tone="orange" />
      </div>

      <div v-loading="dashboard.loading" class="grid min-h-0 min-w-0 flex-1 grid-cols-2 grid-rows-[minmax(0,.98fr)_minmax(0,1.02fr)] gap-4">
        <ChartCard title="Top 应用（按活跃时长）">
          <template #actions>
            <el-select model-value="active" size="small" style="width: 118px">
              <el-option label="按活跃时长" value="active" />
            </el-select>
          </template>
          <div v-if="summary.top_apps.length" class="h-full min-h-0 overflow-auto pr-1">
            <div v-for="item in summary.top_apps" :key="item.name" class="mb-4 flex items-center gap-3">
              <div class="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-blue-50 text-xs font-black text-blue-600">
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
          <div class="flex h-full min-h-0 flex-col">
            <div class="flex min-h-0 flex-1 items-center gap-2 overflow-hidden px-1">
              <div v-for="slot in summary.time_distribution" :key="slot.label" class="flex h-full min-w-0 flex-1 flex-col justify-center">
                <div class="mx-auto w-3 rounded-full transition-all" :class="slot.active ? 'bg-blue-600' : 'bg-slate-200'" :style="{ height: `${slotHeight(slot.active)}px` }"></div>
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
        </ChartCard>

        <ChartCard title="最近活动">
          <template #actions>
            <RouterLink to="/data" class="text-sm font-bold text-blue-600">查看全部</RouterLink>
          </template>
          <div v-if="summary.recent_activities.length" class="h-full min-h-0 overflow-auto">
            <div v-for="item in summary.recent_activities" :key="`${item.time}-${item.title}`" class="flex min-w-0 items-center gap-3 border-b border-slate-100 py-3 last:border-0">
              <div class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-emerald-50 font-bold text-emerald-600">{{ item.source.slice(0, 1) || 'D' }}</div>
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-bold text-slate-800">{{ item.title || item.source }}</div>
                <div class="truncate text-xs text-slate-500">{{ item.source }}</div>
              </div>
              <el-tag effect="light" round>{{ item.time }}</el-tag>
            </div>
          </div>
          <EmptyState v-else title="暂无最近活动" />
        </ChartCard>

        <div class="grid min-h-0 grid-rows-[136px_minmax(0,1fr)] gap-4">
          <ChartCard title="快捷入口">
            <div class="grid h-full grid-cols-3 gap-3">
              <RouterLink class="quick-card" to="/data"><DataLine />数据中心<span>查看与管理数据</span></RouterLink>
              <RouterLink class="quick-card green" to="/workbench"><Files />日报工作台<span>生成与导出日报</span></RouterLink>
              <RouterLink class="quick-card purple" to="/settings"><Setting />设置<span>应用与偏好设置</span></RouterLink>
            </div>
          </ChartCard>
          <ChartCard title="本周趋势">
            <div ref="trendRef" class="h-full min-h-0"></div>
          </ChartCard>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import * as echarts from 'echarts'
import { Clock, CopyDocument, DataLine, Files, Grid, Lightning, Monitor, Refresh, Setting } from '@element-plus/icons-vue'
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

function topPercent(value: number) {
  return Math.max(2, Math.round((value / maxTop.value) * 100))
}

function slotHeight(active: number) {
  return active ? Math.max(26, Math.round((active / maxSlot.value) * 118)) : 54
}

function secondsText(value: number) {
  if (value >= 3600) return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`
  return `${Math.floor(value / 60)}m`
}

async function load() {
  await dashboard.load(app.currentDate)
  await nextTick()
  renderTrend()
}

function renderTrend() {
  if (!trendRef.value) return
  trendChart = trendChart || echarts.init(trendRef.value)
  trendChart.setOption({
    grid: { top: 12, left: 32, right: 18, bottom: 28 },
    xAxis: { type: 'category', data: summary.value.weekly_trend.map((item) => item.date.slice(5)), axisTick: { show: false }, axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#e8eef7' } }, axisLabel: { color: '#94a3b8' } },
    series: [{ type: 'line', smooth: true, symbolSize: 7, data: summary.value.weekly_trend.map((item) => item.count), lineStyle: { width: 3, color: '#2563eb' }, itemStyle: { color: '#2563eb' }, areaStyle: { color: 'rgba(37, 99, 235, .08)' } }]
  })
}

onMounted(load)
watch(() => app.currentDate, load)
</script>

<style scoped>
.quick-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  overflow: hidden;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: #eff6ff;
  padding: 14px;
  font-weight: 900;
  color: #1d4ed8;
}

.quick-card svg {
  width: 24px;
  height: 24px;
}

.quick-card span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 700;
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
