<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { Check, CopyDocument, Download, Refresh } from '@element-plus/icons-vue'

import type { ReportResultView } from '../../types/reportWorkbench'

const props = defineProps<{
  markdown: string
  promptText: string
  loading: boolean
  canGenerate: boolean
  saved: boolean
  selectedDate: string
  templateName: string
}>()

const emit = defineEmits<{
  regenerate: []
  copy: [text: string]
  save: []
}>()

const activeView = shallowRef<ReportResultView>('preview')

const previewBlocks = computed(() =>
  props.markdown
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
)

function exportMarkdown(): void {
  if (!props.markdown) {
    return
  }
  const blob = new Blob([props.markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `daily-report-${props.selectedDate}.md`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <section class="workbench-card result-card">
    <header class="result-header">
      <div>
        <h2 class="card-title">生成结果预览</h2>
        <p class="card-subtitle">Markdown 预览、原文和本次 Prompt 会保留在这里</p>
      </div>
      <div class="result-actions">
        <el-button :icon="Refresh" :loading="loading" :disabled="!markdown" @click="emit('regenerate')">重新生成</el-button>
        <el-button :icon="CopyDocument" :disabled="!markdown" @click="emit('copy', markdown)">复制 Markdown</el-button>
        <el-button :icon="Download" :disabled="!markdown" @click="exportMarkdown">导出 .md</el-button>
        <el-button :icon="Check" type="success" plain :disabled="!markdown || saved" @click="emit('save')">
          {{ saved ? '已保存' : '保存日报' }}
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="!canGenerate && !markdown"
      class="result-alert"
      type="warning"
      show-icon
      :closable="false"
      title="请先选择至少一条非敏感素材。"
    />

    <el-tabs v-model="activeView" class="result-tabs">
      <el-tab-pane label="Markdown 预览" name="preview">
        <div v-if="loading" class="result-loading">
          <el-icon class="loading-icon"><Refresh /></el-icon>
          <strong>正在生成日报...</strong>
          <span>正在整理素材、调用模型并生成 Markdown</span>
        </div>
        <div v-else-if="markdown" class="markdown-preview">
          <template v-for="(block, index) in previewBlocks" :key="`${index}-${block.slice(0, 12)}`">
            <h3 v-if="block.startsWith('### ')" class="md-h3">{{ block.replace(/^###\s*/, '') }}</h3>
            <h2 v-else-if="block.startsWith('## ')" class="md-h2">{{ block.replace(/^##\s*/, '') }}</h2>
            <h1 v-else-if="block.startsWith('# ')" class="md-h1">{{ block.replace(/^#\s*/, '') }}</h1>
            <pre v-else-if="block.startsWith('```')" class="md-code">{{ block }}</pre>
            <p v-else class="md-paragraph">{{ block }}</p>
          </template>
        </div>
        <el-empty v-else description="请选择素材并配置 Prompt，然后点击“生成日报”。" />
      </el-tab-pane>

      <el-tab-pane label="原始 Markdown" name="markdown">
        <el-input :model-value="markdown" type="textarea" :rows="16" resize="none" readonly placeholder="暂无生成结果" />
      </el-tab-pane>

      <el-tab-pane label="Prompt" name="prompt">
        <el-input :model-value="promptText" type="textarea" :rows="16" resize="none" readonly placeholder="尚未构建 Prompt" />
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<style scoped>
.result-card {
  min-width: 0;
}

.result-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.card-title {
  margin: 0;
  color: #172033;
  font-size: 16px;
  font-weight: 840;
}

.card-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}

.result-actions {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.result-alert {
  margin-bottom: 10px;
}

.result-tabs {
  min-width: 0;
}

.markdown-preview,
.result-loading {
  min-height: 260px;
  max-height: 420px;
  overflow: auto;
  padding: 18px;
  border: 1px solid #e3ebf6;
  border-radius: 12px;
  background: #fbfdff;
}

.result-loading {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  color: #526070;
}

.loading-icon {
  color: #2563eb;
  animation: result-spin 900ms linear infinite;
}

.md-h1,
.md-h2,
.md-h3 {
  color: #172033;
  letter-spacing: 0;
}

.md-h1 {
  margin: 0 0 14px;
  font-size: 24px;
}

.md-h2 {
  margin: 18px 0 10px;
  font-size: 18px;
}

.md-h3 {
  margin: 14px 0 8px;
  font-size: 15px;
}

.md-paragraph {
  margin: 0 0 10px;
  color: #344054;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.7;
}

.md-code {
  max-width: 100%;
  overflow-x: auto;
  padding: 12px;
  border-radius: 8px;
  background: #172033;
  color: #e5edf7;
}

@keyframes result-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 960px) {
  .result-header {
    flex-direction: column;
  }

  .result-actions {
    justify-content: flex-start;
  }
}
</style>
