<script setup lang="ts">
import { Calendar } from '@element-plus/icons-vue'

import FeaturePlaceholder from '../components/FeaturePlaceholder.vue'
import PageLayout from '../layouts/PageLayout.vue'

const sections = [
  {
    title: '关键指标',
    description: '预留有效工作时长、采集数量、敏感项和日报状态。'
  },
  {
    title: '应用分布',
    description: '预留 Top 应用、分类分布和时间占比图。'
  },
  {
    title: '活动节奏',
    description: '预留 24 小时活动节奏和最近高价值素材。'
  },
  {
    title: '日报入口',
    description: '预留一键生成日报、刷新数据和日期切换操作。'
  }
]
</script>

<template>
  <PageLayout title="今日总览" subtitle="总览当天采集状态、工作节奏和日报生成进度。" scrollable>
    <FeaturePlaceholder
      :icon="Calendar"
      title="今日总览界面"
      description="这里后续会承载首页仪表盘，目前仅搭建页面框架和模块区域。"
      :sections="sections"
    />
  </PageLayout>
</template>
