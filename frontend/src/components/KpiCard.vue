<script setup lang="ts">
/**
 * KPI 卡片骨架。
 *
 * 作用：
 * - 保留 title/value/unit/icon 等指标展示契约
 * - 具体指标卡布局由后续实现补充
 */

withDefaults(defineProps<{
  title: string
  value: string | number
  unit?: string
  icon?: unknown
  iconText?: string
  tone?: 'blue' | 'green' | 'purple' | 'orange' | 'gray'
}>(), {
  tone: 'blue'
})
</script>

<template>
  <section class="kpi-card app-card">
    <!-- 待实现：指标图标、标题、数值、单位、趋势等。 -->
    <slot />
  </section>
</template>

<style scoped>
.kpi-card {
  min-width: 0;
}
</style>
