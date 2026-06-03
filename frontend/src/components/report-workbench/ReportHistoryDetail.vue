<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import {
  ChatDotRound,
  Collection,
  CopyDocument,
  Delete,
  Download,
  Link,
  MagicStick,
  Monitor,
  Tickets,
  View
} from '@element-plus/icons-vue'

import type { ReportHistoryRow } from '../../types/reportWorkbench'

type DetailTab = 'preview' | 'markdown' | 'materials' | 'versions'

const props = defineProps<{
  report: ReportHistoryRow | null
  loading: boolean
}>()

const emit = defineEmits<{
  copy: [text: string]
  export: [report: ReportHistoryRow]
  viewPrompt: [prompt: string]
  regenerate: [report: ReportHistoryRow]
  delete: [id: number]
}>()

const activeTab = shallowRef<DetailTab>('preview')

const sourceCards = computed(() => {
  const counts = props.report?.source_counts ?? {}
  const items = [
    { key: 'app', label: '前台应用', value: Number(counts.app || 0), icon: Monitor, tone: 'blue' },
    { key: 'browser', label: '浏览器历史', value: Number(counts.browser || 0), icon: Link, tone: 'green' },
    { key: 'clipboard', label: '剪切板', value: Number(counts.clipboard || 0), icon: Tickets, tone: 'orange' },
    { key: 'ai_prompt', label: 'AI 提问', value: Number(counts.ai_prompt || 0), icon: ChatDotRound, tone: 'purple' }
  ]
  const total = items.reduce((sum, item) => sum + item.value, 0)
  return [...items, { key: 'all', label: '全部素材', value: total, icon: Collection, tone: 'slate' }]
})

const infoItems = computed(() => {
  const report = props.report
  if (!report) return []
  return [
    { label: '生成时间', value: formatCreatedAt(report.created_at) },
    { label: '模板名称', value: report.template_name || '-' },
    { label: '模型', value: report.model_name || '-' },
    { label: '字数', value: (report.report_markdown || '').length.toLocaleString() },
    { label: '使用素材数', value: String(sourceCards.value[sourceCards.value.length - 1]?.value ?? 0) },
    { label: '敏感排除数', value: String(Number(report.source_counts?.sensitive_excluded_count || 0)) }
  ]
})

const previewBlocks = computed(() =>
  (props.report?.report_markdown || '')
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
)

function formatCreatedAt(value?: string): string {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function blockText(block: string, marker: string): string {
  return block.replace(new RegExp(`^${marker}\\s*`), '')
}
</script>

<template>
  <section v-loading="loading" class="history-detail-card">
    <template v-if="report">
      <header class="detail-header">
        <div class="detail-heading">
          <h2 class="detail-title">{{ report.date }} 日报</h2>
          <p class="detail-subtitle">
            {{ report.template_name || 'daily_standard' }} · {{ report.model_name || '模型未记录' }}
            <el-tag size="small" type="success" effect="light">已保存</el-tag>
          </p>
        </div>
        <div class="detail-actions">
          <el-button :icon="View" @click="emit('viewPrompt', report.prompt_text || '')">查看 Prompt</el-button>
          <el-button :icon="CopyDocument" @click="emit('copy', report.report_markdown || '')">复制 Markdown</el-button>
          <el-button :icon="Download" @click="emit('export', report)">导出 .md</el-button>
          <el-button :icon="MagicStick" plain @click="emit('regenerate', report)">重新生成</el-button>
          <el-button :icon="Delete" type="danger" plain @click="emit('delete', report.id)">删除日报</el-button>
        </div>
      </header>

      <dl class="info-grid">
        <div v-for="item in infoItems" :key="item.label" class="info-card">
          <dt>{{ item.label }}</dt>
          <dd>{{ item.value }}</dd>
        </div>
      </dl>

      <section class="material-overview">
        <h3>素材概览</h3>
        <div class="source-strip">
          <span v-for="item in sourceCards" :key="item.key" class="source-card" :class="`source-card--${item.tone}`">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>
              <em>{{ item.label }}</em>
              <strong>{{ item.value }} 条</strong>
            </span>
          </span>
        </div>
      </section>

      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="日报预览" name="preview">
          <div class="markdown-preview">
            <template v-for="(block, index) in previewBlocks" :key="`${index}-${block.slice(0, 20)}`">
              <h3 v-if="block.startsWith('### ')" class="md-h3">{{ blockText(block, '###') }}</h3>
              <h2 v-else-if="block.startsWith('## ')" class="md-h2">{{ blockText(block, '##') }}</h2>
              <h1 v-else-if="block.startsWith('# ')" class="md-h1">{{ blockText(block, '#') }}</h1>
              <pre v-else-if="block.startsWith('```')" class="md-code">{{ block }}</pre>
              <p v-else class="md-paragraph">{{ block }}</p>
            </template>
            <el-empty v-if="!previewBlocks.length" description="暂无日报正文" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="原始 Markdown" name="markdown">
          <pre class="raw-block">{{ report.report_markdown || '暂无日报正文' }}</pre>
        </el-tab-pane>

        <el-tab-pane label="素材明细" name="materials">
          <pre class="raw-block">{{ report.material_snapshot_json || report.material_summary || '暂无素材快照' }}</pre>
        </el-tab-pane>

        <el-tab-pane label="版本历史" name="versions">
          <div class="version-empty">
            <strong>当前版本</strong>
            <span>{{ formatCreatedAt(report.updated_at || report.created_at) }}</span>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-empty v-else description="请选择一篇历史日报查看详情" />
  </section>
</template>

<style scoped>
.history-detail-card {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 12px;
  padding: 18px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}

.detail-header {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.detail-heading {
  min-width: 0;
}

.detail-title {
  margin: 0;
  color: #172033;
  font-size: 24px;
  font-weight: 860;
  line-height: 1.2;
  white-space: nowrap;
}

.detail-subtitle {
  margin: 8px 0 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: #526070;
  font-size: 13px;
}

.detail-actions {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(3, max-content);
  justify-content: flex-end;
  gap: 8px;
}

.detail-actions :deep(.el-button) {
  min-height: 36px;
  margin-left: 0;
  border-radius: 8px;
}

.info-grid {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.info-card {
  min-width: 0;
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  background: #fbfdff;
}

.info-card dt,
.info-card dd {
  min-width: 0;
  margin: 0;
}

.info-card dt {
  color: #667085;
  font-size: 12px;
}

.info-card dd {
  overflow: hidden;
  color: #172033;
  font-size: 15px;
  font-weight: 820;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-overview {
  min-width: 0;
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  background: #fbfdff;
}

.material-overview h3 {
  margin: 0;
  color: #172033;
  font-size: 14px;
  font-weight: 840;
}

.source-strip {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.source-card {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #fff;
}

.source-card .el-icon {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #f3f7ff;
}

.source-card :deep(svg) {
  width: 18px;
  height: 18px;
}

.source-card span {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.source-card em {
  overflow: hidden;
  color: #526070;
  font-size: 12px;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-card strong {
  color: #172033;
  font-size: 14px;
  font-weight: 820;
}

.source-card--blue :deep(svg) {
  color: #2563eb;
}

.source-card--green :deep(svg) {
  color: #16a34a;
}

.source-card--orange :deep(svg) {
  color: #ea580c;
}

.source-card--purple :deep(svg) {
  color: #7c3aed;
}

.source-card--slate :deep(svg) {
  color: #526179;
}

.detail-tabs {
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.detail-tabs :deep(.el-tabs__content) {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-tabs :deep(.el-tab-pane) {
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.markdown-preview,
.raw-block,
.version-empty {
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 18px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  background: #fbfdff;
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

.md-code,
.raw-block {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: #344054;
  font: inherit;
  line-height: 1.65;
}

.version-empty {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 6px;
  color: #667085;
}

.version-empty strong {
  color: #172033;
}

@media (max-width: 1280px) {
  .info-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .source-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1020px) {
  .detail-header {
    grid-template-columns: minmax(0, 1fr);
  }

  .detail-actions {
    grid-template-columns: repeat(auto-fit, minmax(128px, max-content));
    justify-content: flex-start;
  }

  .detail-title {
    white-space: normal;
  }
}

@media (max-width: 620px) {
  .info-grid,
  .source-strip {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
