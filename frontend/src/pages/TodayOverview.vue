<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'

import { callTypedBridge } from '../api/bridge'
import type { GeneratedReport, MaterialCard, OverviewPayload } from '../api/types'
import PageLayout from '../layouts/PageLayout.vue'

/**
 * 今日总览页骨架。
 *
 * 页面职责：
 * - 读取当天概览统计：getOverview
 * - 读取可用于日报的高价值素材：getReportMaterials
 * - 预留“生成日报”入口：generateReport
 *
 * 布局实现建议：
 * - 顶部：日期选择、刷新按钮、生成日报按钮
 * - 主体：KPI 区、Top 应用图、数据源分布、24 小时活动节律、近期素材
 */

const today = new Date().toISOString().slice(0, 10)

const date = shallowRef(today)
const loading = shallowRef(false)
const generating = shallowRef(false)
const lastError = shallowRef('')
const overview = shallowRef<OverviewPayload | null>(null)
const materials = shallowRef<MaterialCard[]>([])

async function loadOverview(): Promise<void> {
  loading.value = true
  lastError.value = ''

  try {
    const [overviewPayload, materialPayload] = await Promise.all([
      callTypedBridge('getOverview', { date: date.value }),
      callTypedBridge('getReportMaterials', { date: date.value })
    ])

    overview.value = overviewPayload
    materials.value = materialPayload.items
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function generateDailyReport(): Promise<GeneratedReport | null> {
  generating.value = true
  lastError.value = ''

  try {
    return await callTypedBridge('generateReport', {
      date: date.value,
      templateName: 'daily_standard'
    })
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
    return null
  } finally {
    generating.value = false
  }
}

onMounted(loadOverview)

defineExpose({
  date,
  loading,
  generating,
  lastError,
  overview,
  materials,
  loadOverview,
  generateDailyReport
})
</script>

<template>
  <PageLayout title="今日总览" scrollable>
    <!--
      actions slot 预留：
      - 日期选择器绑定 date
      - 刷新按钮调用 loadOverview()
      - 生成日报按钮调用 generateDailyReport()
    -->

    <section class="page-skeleton" v-loading="loading">
      <!--
        数据状态：
        - overview: OverviewPayload | null
        - materials: MaterialCard[]
        - lastError: string

        后端接口：
        - getOverview({ date }) -> OverviewPayload
        - getReportMaterials({ date }) -> { items: MaterialCard[] }
        - generateReport({ date, templateName }) -> GeneratedReport

        待实现页面区域：
        1. 今日有效工作时长、四类数据源数量、日报状态
        2. Top 应用条形图
        3. 数据源分布
        4. 24 小时活动节律
        5. 最近高价值素材列表
      -->
    </section>
  </PageLayout>
</template>

<style scoped>
.page-skeleton {
  min-height: 100%;
}
</style>
