<script setup lang="ts">
import { computed, shallowReactive, watch } from 'vue'

import type { EChartsOption } from 'echarts'
import { callTypedBridge } from '../../api/bridge'
import LazyChartCard from './LazyChartCard.vue'
import type { DataCenterFilters } from './types'
import { dateRangeToPayload } from './types'

const props = defineProps<{
  filters: DataCenterFilters
  active: boolean
  refreshKey: number
}>()

const loadedCharts = shallowReactive<Record<string, boolean>>({})
const chartData = shallowReactive<Record<string, Array<Record<string, unknown>>>>({})
const loadingCharts = shallowReactive<Record<string, boolean>>({})
const chartRequestIds = shallowReactive<Record<string, number>>({})

const chartCards = [
  { key: 'dailyRecordTrend', title: '每日记录量趋势', description: '按来源聚合每日采集记录量', span: 4 },
  { key: 'sensitiveSourceDistribution', title: '敏感记录来源', description: '按来源统计敏感记录', span: 2 },
  { key: 'hourlyHeatmap', title: '小时活动热力', description: '按日期和小时聚合应用活跃时长', wide: true, span: 6 },
  { key: 'appDurationRanking', title: '应用使用时长排行', description: '按应用聚合活跃时长', span: 3 },
  { key: 'domainRanking', title: '高频域名排行', description: '浏览器历史中的访问域名', span: 3 }
]

const chartOptions = computed<Record<string, EChartsOption | null>>(() => {
  return Object.fromEntries(chartCards.map((chart) => [chart.key, optionFor(chart.key)]))
})
const filterSignature = computed(() => {
  const range = dateRangeToPayload(props.filters)
  return JSON.stringify({
    ...range,
    sourceTypes: [...props.filters.sourceTypes],
    sensitive: props.filters.sensitive,
    categories: [...props.filters.categories],
    keyword: props.filters.keyword.trim(),
    sortOrder: props.filters.sortOrder
  })
})

async function loadChart(chartType: string): Promise<void> {
  if (loadingCharts[chartType]) {
    return
  }
  const requestId = (chartRequestIds[chartType] ?? 0) + 1
  chartRequestIds[chartType] = requestId
  loadedCharts[chartType] = true
  loadingCharts[chartType] = true
  try {
    const range = dateRangeToPayload(props.filters)
    const response = await callTypedBridge('getDataCenterAnalytics', {
      ...range,
      filters: bridgeFilters(),
      chartTypes: [chartType]
    })
    if (chartRequestIds[chartType] === requestId) {
      chartData[chartType] = Array.isArray(response.charts[chartType]) ? response.charts[chartType] : []
    }
  } finally {
    if (chartRequestIds[chartType] === requestId) {
      loadingCharts[chartType] = false
    }
  }
}

function bridgeFilters() {
  return {
    sourceTypes: props.filters.sourceTypes,
    sensitive: props.filters.sensitive === 'all' ? undefined : props.filters.sensitive === 'sensitive',
    categories: props.filters.categories,
    keyword: props.filters.keyword.trim() || undefined,
    sortOrder: props.filters.sortOrder
  }
}

function optionFor(chartType: string): EChartsOption | null {
  const rows = chartData[chartType]
  if (!rows?.length) {
    return null
  }
  if (chartType === 'dailyRecordTrend') {
    return {
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      animation: false,
      grid: { left: 36, right: 16, top: 24, bottom: 48 },
      xAxis: { type: 'category', data: rows.map((row) => String(row.date || '')) },
      yAxis: { type: 'value' },
      series: [
        {
          name: '总计',
          type: 'line' as const,
          smooth: true,
          lineStyle: { width: 3 },
          data: rows.map((row) => (
            Number(row.app_count || 0)
            + Number(row.browser_count || 0)
            + Number(row.clipboard_count || 0)
            + Number(row.ai_prompt_count || 0)
            + Number(row.browser_event_count || 0)
          ))
        },
        seriesLine('应用', rows, 'app_count'),
        seriesLine('浏览', rows, 'browser_count'),
        seriesLine('剪切板', rows, 'clipboard_count'),
        seriesLine('AI', rows, 'ai_prompt_count'),
        seriesLine('浏览器事件', rows, 'browser_event_count')
      ] as EChartsOption['series']
    }
  }
  if (chartType === 'hourlyHeatmap') {
    const dates = [...new Set(rows.map((row) => String(row.date)))]
    const maxMinutes = Math.max(...rows.map((row) => Math.round(Number(row.active_duration_sec || 0) / 60)), 1)
    return {
      animation: false,
      tooltip: {
        formatter: (params: unknown) => {
          const value = Array.isArray((params as { value?: unknown }).value)
            ? ((params as { value: unknown[] }).value)
            : []
          const hour = Number(value[0] ?? 0)
          const date = dates[Number(value[1] ?? 0)] ?? '-'
          const minutes = Number(value[2] ?? 0)
          return `${date}<br/>${String(hour).padStart(2, '0')}:00 - ${String(hour + 1).padStart(2, '0')}:00<br/>活跃 ${minutes} 分钟`
        }
      },
      grid: { left: 74, right: 20, top: 24, bottom: 58 },
      xAxis: {
        type: 'category',
        data: Array.from({ length: 24 }, (_, index) => `${index}:00`),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#d8e2ef' } },
        axisLabel: { color: '#7b8797', interval: 2 }
      },
      yAxis: {
        type: 'category',
        data: dates,
        axisTick: { show: false },
        axisLine: { lineStyle: { color: '#d8e2ef' } },
        axisLabel: {
          color: '#7b8797',
          formatter: (value: string) => value.slice(5)
        }
      },
      visualMap: {
        min: 0,
        max: maxMinutes,
        orient: 'horizontal',
        left: 'center',
        bottom: 8,
        itemWidth: 12,
        itemHeight: 84,
        text: ['高', '低'],
        inRange: {
          color: ['#eef6ff', '#bfdbfe', '#60a5fa', '#2563eb', '#1e3a8a']
        }
      },
      series: [{
        type: 'heatmap',
        data: rows.map((row) => [
          Number(row.hour || 0),
          dates.indexOf(String(row.date)),
          Math.round(Number(row.active_duration_sec || 0) / 60)
        ]),
        emphasis: {
          itemStyle: {
            borderColor: '#172033',
            borderWidth: 1
          }
        },
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 2,
          borderRadius: 3
        }
      }]
    }
  }
  if (chartType === 'sensitiveSourceDistribution') {
    return {
      tooltip: { trigger: 'item' },
      animation: false,
      series: [{
        type: 'pie',
        radius: ['45%', '70%'],
        data: rows.map((row) => ({ name: sourceTypeLabel(String(row.source_type || '-')), value: Number(row.count || 0) }))
      }]
    }
  }
  const nameKey = chartType === 'domainRanking' ? 'domain' : 'name'
  const valueKey = chartType === 'domainRanking' ? 'count' : 'active_duration_sec'
  const durationScale = durationAxisScale(rows, valueKey)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const item = Array.isArray(params) ? params[0] as { name?: string; value?: unknown } : params as { name?: string; value?: unknown }
        if (chartType === 'appDurationRanking') {
          return `${item.name || '-'}<br/>${formatScaledDuration(Number(item.value || 0), durationScale.unit)}`
        }
        return `${item.name || '-'}<br/>${Number(item.value || 0)} 次`
      }
    },
    animation: false,
    grid: { left: 118, right: 20, top: 20, bottom: 34 },
    xAxis: {
      type: 'value',
      name: chartType === 'appDurationRanking' ? durationScale.label : '次数',
      nameTextStyle: { color: '#7b8797' },
      axisLabel: { color: '#7b8797' }
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => truncateLabel(String(row[nameKey] || '-'), 18)).reverse(),
      axisLabel: { color: '#536174', width: 108, overflow: 'truncate' }
    },
    series: [{
      type: 'bar',
      data: rows.map((row) => scaleValue(Number(row[valueKey] || 0), durationScale.unit, chartType)).reverse()
    }]
  }
}

function seriesLine(name: string, rows: Array<Record<string, unknown>>, key: string) {
  return {
    name,
    type: 'line' as const,
    smooth: true,
    data: rows.map((row) => Number(row[key] || 0))
  }
}

function truncateLabel(value: string, maxLength: number): string {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value
}

function durationAxisScale(rows: Array<Record<string, unknown>>, valueKey: string): { unit: 'minute' | 'hour'; label: string } {
  const maxSeconds = Math.max(...rows.map((row) => Number(row[valueKey] || 0)), 0)
  return maxSeconds >= 7200 ? { unit: 'hour', label: '小时' } : { unit: 'minute', label: '分钟' }
}

function scaleValue(value: number, unit: 'minute' | 'hour', chartType: string): number {
  if (chartType !== 'appDurationRanking') {
    return value
  }
  const divisor = unit === 'hour' ? 3600 : 60
  return Number((value / divisor).toFixed(1))
}

function formatScaledDuration(value: number, unit: 'minute' | 'hour'): string {
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${unit === 'hour' ? '小时' : '分钟'}`
}

function sourceTypeLabel(value: string): string {
  return {
    app: '应用',
    browser: '浏览器',
    clipboard: '剪贴板',
    ai_prompt: 'AI 提问'
    ,browser_event: '浏览器事件'
  }[value] ?? value
}

watch(
  () => [filterSignature.value, props.refreshKey],
  () => {
    for (const key of Object.keys(loadedCharts)) {
      if (loadedCharts[key]) {
        void loadChart(key)
      }
    }
  }
)

watch(
  () => props.active,
  (active) => {
    if (!active || loadedCharts[chartCards[0].key]) {
      return
    }
    void loadChart(chartCards[0].key)
  },
  { immediate: true }
)
</script>

<template>
  <section class="analysis-view">
    <div class="chart-grid">
      <LazyChartCard
        v-for="chart in chartCards"
        :key="chart.key"
        :title="chart.title"
        :description="chart.description"
        :option="chartOptions[chart.key]"
        :loading="Boolean(loadingCharts[chart.key])"
        :loaded="Boolean(loadedCharts[chart.key])"
        :wide="chart.wide"
        :span="chart.span"
        @load="loadChart(chart.key)"
      />
    </div>
  </section>
</template>

<style scoped>
.analysis-view {
  height: 100%;
  min-height: 0;
  min-width: 0;
  display: grid;
  align-content: start;
  padding: 14px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  overflow: auto;
  scrollbar-gutter: stable;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
}

@media (max-width: 1040px) {
  .chart-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
