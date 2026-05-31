<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'

import type { EChartsOption } from 'echarts'

const props = defineProps<{
  title: string
  description: string
  option: EChartsOption | null
  loading: boolean
  wide?: boolean
  span?: number
  loaded?: boolean
}>()

const emit = defineEmits<{
  load: []
}>()

const chartEl = shallowRef<HTMLDivElement | null>(null)
const loaded = shallowRef(false)
const effectiveLoaded = computed(() => loaded.value || Boolean(props.loaded))
const cardStyle = computed(() => ({
  '--chart-span': String(props.span ?? (props.wide ? 2 : 1))
}))
let chart: echarts.ECharts | null = null
let observer: IntersectionObserver | null = null
let resizeObserver: ResizeObserver | null = null
let resizeFrame = 0

function requestLoad(): void {
  if (loaded.value) {
    return
  }
  loaded.value = true
  emit('load')
}

function renderChart(): void {
  if (!props.option) {
    chart?.clear()
    return
  }
  if (!chartEl.value) {
    return
  }
  chart ||= echarts.init(chartEl.value)
  chart.setOption(props.option, true)
  scheduleResize()
}

function scheduleResize(): void {
  if (resizeFrame) {
    return
  }
  resizeFrame = window.requestAnimationFrame(() => {
    resizeFrame = 0
    chart?.resize()
  })
}

onMounted(() => {
  if (chartEl.value) {
    observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        requestLoad()
      }
    }, { rootMargin: '120px' })
    observer.observe(chartEl.value)
    resizeObserver = new ResizeObserver(scheduleResize)
    resizeObserver.observe(chartEl.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  resizeObserver?.disconnect()
  if (resizeFrame) {
    window.cancelAnimationFrame(resizeFrame)
  }
  chart?.dispose()
})

watch(
  () => props.option,
  async () => {
    await nextTick()
    renderChart()
  },
  { flush: 'post' }
)
</script>

<template>
  <article class="chart-card" :class="{ 'chart-card--wide': wide }" :style="cardStyle">
    <header class="chart-header">
      <div>
        <h3 class="chart-title">{{ title }}</h3>
        <p class="chart-description">{{ description }}</p>
      </div>
    </header>
    <div v-loading="loading" class="chart-canvas-shell">
      <div ref="chartEl" v-show="option" class="chart-canvas"></div>
      <el-empty v-if="effectiveLoaded && !loading && !option" class="chart-empty" description="暂无统计数据" />
    </div>
  </article>
</template>

<style scoped>
.chart-card {
  min-width: 0;
  min-height: 0;
  grid-column: span var(--chart-span, 1);
  padding: 16px;
  border: 1px solid #dfe8f5;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 31, 61, 0.04);
  animation: chart-card-rise 360ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.chart-card--wide {
  grid-column: span var(--chart-span, 2);
}

.chart-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.chart-title {
  margin: 0;
  color: #172033;
  font-size: 15px;
  font-weight: 820;
}

.chart-description {
  margin: 5px 0 0;
  color: #708094;
  font-size: 12px;
  line-height: 1.45;
}

.chart-canvas-shell {
  position: relative;
  height: 300px;
  min-width: 0;
  min-height: 0;
}

.chart-canvas {
  width: 100%;
  height: 100%;
}

.chart-empty {
  height: 100%;
}

@media (max-width: 1040px) {
  .chart-card,
  .chart-card--wide {
    grid-column: span 1;
  }
}

@keyframes chart-card-rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .chart-card {
    animation: none;
  }
}
</style>
