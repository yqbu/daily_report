<script setup lang="ts">
import { Setting } from '@element-plus/icons-vue'

import FeaturePlaceholder from '../components/FeaturePlaceholder.vue'
import PageLayout from '../layouts/PageLayout.vue'

const sections = [
  {
    title: '采集设置',
    description: '预留前台应用、剪贴板、浏览器历史和 AI Prompt 开关。'
  },
  {
    title: '隐私规则',
    description: '预留敏感词、默认隐藏、人工确认和剪贴板预览规则。'
  },
  {
    title: '模型设置',
    description: '预留模型供应商、接口地址、密钥、温度和超时配置。'
  },
  {
    title: '系统信息',
    description: '预留健康状态、日志保留、YASB 联动和配置文件路径。'
  }
]
</script>

<template>
  <PageLayout title="设置" subtitle="管理采集、隐私、模型、日志和桌面集成选项。" scrollable>
    <FeaturePlaceholder
      :icon="Setting"
      title="设置界面"
      description="这里后续会承载配置表单和运行状态，目前仅搭建页面框架和模块区域。"
      :sections="sections"
    />
  </PageLayout>
</template>
