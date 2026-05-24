<script setup lang="ts">
import TodayOverview from './TodayOverview.vue'

/**
 * 旧 DashboardPage 兼容入口。
 *
 * 当前正式路由使用 TodayOverview.vue。
 * 保留这个文件是为了避免历史 import 失效，不再在这里维护独立页面实现。
 */
</script>

<template>
  <TodayOverview />
</template>
