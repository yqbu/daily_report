<script setup lang="ts">
import { Document } from '@element-plus/icons-vue'

import FeaturePlaceholder from '../components/FeaturePlaceholder.vue'
import PageLayout from '../layouts/PageLayout.vue'

const sections = [
  {
    title: '素材列表',
    description: '预留已选择材料、敏感项提示和素材摘要。'
  },
  {
    title: 'Prompt 预览',
    description: '预留模板选择、Prompt 构建和复制操作。'
  },
  {
    title: 'Markdown 预览',
    description: '预留日报生成结果、导出和复制操作。'
  },
  {
    title: '历史日报',
    description: '预留历史记录列表、日期切换和报告回看。'
  }
]
</script>

<template>
  <PageLayout title="日报工作台" subtitle="从已选材料构建 Prompt，并生成、预览、管理日报。" scrollable>
    <FeaturePlaceholder
      :icon="Document"
      title="日报工作台界面"
      description="这里后续会承载素材、Prompt、日报预览和历史报告，目前仅搭建页面框架和模块区域。"
      :sections="sections"
    />
  </PageLayout>
</template>
