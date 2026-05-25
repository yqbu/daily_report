<script setup lang="ts">
import { DataAnalysis } from '@element-plus/icons-vue'

import FeaturePlaceholder from '../components/FeaturePlaceholder.vue'
import PageLayout from '../layouts/PageLayout.vue'

const sections = [
  {
    title: '筛选工具栏',
    description: '预留日期、来源、选中状态、敏感状态和关键词筛选。'
  },
  {
    title: '时间线视图',
    description: '预留按时间顺序聚合展示四类采集记录。'
  },
  {
    title: '数据表格',
    description: '预留 App、浏览器、剪贴板和 AI Prompt 的分页表格。'
  },
  {
    title: '详情抽屉',
    description: '预留原始字段、分类、备注、重要性和选择状态编辑。'
  }
]
</script>

<template>
  <PageLayout title="数据中心" subtitle="统一查看、筛选和整理本地采集到的工作材料。" scrollable>
    <FeaturePlaceholder
      :icon="DataAnalysis"
      title="数据中心界面"
      description="这里后续会承载时间线、表格和记录详情，目前仅搭建页面框架和模块区域。"
      :sections="sections"
    />
  </PageLayout>
</template>
