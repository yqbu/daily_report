<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import {
  Calendar,
  Collection,
  CopyDocument,
  DataAnalysis,
  Document,
  Link,
  Lock,
  Monitor,
  Tickets
} from '@element-plus/icons-vue'

import type { ReportHistoryRow, ReportSourceTotals } from '../../types/reportWorkbench'

type DetailTab = 'info' | 'preview' | 'markdown' | 'prompt' | 'materials'

const props = defineProps<{
  report: ReportHistoryRow | null
  reportVersions: ReportHistoryRow[]
  sourceTotals: ReportSourceTotals
  loading: boolean
}>()

const emit = defineEmits<{
  selectVersion: [id: number]
}>()

const activeTab = shallowRef<DetailTab>('info')

const sourceCards = computed(() => {
  const counts = props.report?.source_counts ?? {}
  const browserCount = browserSourceCount(counts)
  const items = [
    { key: 'app', label: '前台应用', value: Number(counts.app || 0), total: props.sourceTotals.app, icon: Monitor, tone: 'blue' },
    { key: 'browser', label: '浏览器', value: browserCount, total: props.sourceTotals.browser, icon: Link, tone: 'green' },
    { key: 'clipboard', label: '剪切板', value: Number(counts.clipboard || 0), total: props.sourceTotals.clipboard, icon: Tickets, tone: 'orange' }
  ]
  const selectedTotal = items.reduce((sum, item) => sum + item.value, 0)
  const availableTotal = props.sourceTotals.total
  const sourceItems = items.map((item) => ({
    ...item,
    percent: item.total > 0 ? Math.round((item.value / item.total) * 1000) / 10 : 0
  }))
  return [
    ...sourceItems,
    {
      key: 'all',
      label: '全部素材',
      value: selectedTotal,
      total: availableTotal,
      icon: Collection,
      tone: 'purple',
      percent: availableTotal > 0 ? Math.round((selectedTotal / availableTotal) * 1000) / 10 : 0
    }
  ]
})

const versionCards = computed(() => {
  const rows = uniqueReports(props.reportVersions.length ? props.reportVersions : props.report ? [props.report] : [])
  const chronological = [...rows].sort(compareReportAsc)
  const latestId = chronological[chronological.length - 1]?.id ?? null
  const versionLabelById = new Map(chronological.map((row, index) => [row.id, `版本 1.0.${index}`]))

  return [...chronological].reverse().map((row) => ({
    row,
    versionLabel: versionLabelById.get(row.id) ?? '版本 1.0.0',
    createdAt: formatCreatedAt(row.created_at),
    templateName: row.template_name || 'daily_standard',
    modelName: row.model_name || '模型未记录',
    materialCount: reportMaterialCount(row),
    isCurrent: row.id === props.report?.id,
    isLatest: row.id === latestId
  }))
})

const infoItems = computed(() => {
  const report = props.report
  if (!report) return []
  return [
    { label: '生成时间', value: formatCreatedAt(report.created_at), icon: Calendar, tone: 'blue' },
    { label: '模板名称', value: report.template_name || '-', icon: Collection, tone: 'indigo' },
    { label: '模型', value: report.model_name || '-', icon: DataAnalysis, tone: 'cyan' },
    { label: '字数', value: (report.report_markdown || '').length.toLocaleString(), suffix: '字', icon: Document, tone: 'orange' },
    { label: '使用素材数', value: String(sourceCards.value[sourceCards.value.length - 1]?.value ?? 0), suffix: '条', icon: CopyDocument, tone: 'green' },
    { label: '敏感排除数', value: String(Number(report.source_counts?.sensitive_excluded_count || 0)), suffix: '条', icon: Lock, tone: 'slate' }
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

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return '0%'
  if (value === 0 || value === 100) return `${value}%`
  return `${value.toFixed(1)}%`
}

function progressWidth(value: number): { width: string } {
  const percent = Math.max(0, Math.min(100, value))
  return { width: `${percent}%` }
}

function sourceTotalLabel(value: number, total: number): string {
  return total > 0 ? `${value} / ${total} 条` : `${value} 条`
}

function browserSourceCount(counts: Record<string, unknown>): number {
  const browser = Number(counts.browser || 0)
  const legacyBrowser = Number(counts.ai_prompt || 0) + Number(counts.browser_event || 0)
  return browser || legacyBrowser
}

function reportMaterialCount(report: ReportHistoryRow): number {
  const counts = report.source_counts ?? {}
  return Number(counts.app || 0) + browserSourceCount(counts) + Number(counts.clipboard || 0)
}

function uniqueReports(reports: ReportHistoryRow[]): ReportHistoryRow[] {
  return Array.from(new Map(reports.map((report) => [report.id, report])).values())
}

function compareReportAsc(left: ReportHistoryRow, right: ReportHistoryRow): number {
  const timeDiff = new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
  return timeDiff || left.id - right.id
}
</script>

<template>
  <section v-loading="loading" class="history-detail-card">
    <template v-if="report">
      <el-tabs type="card" v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="日报信息" name="info">
          <div class="detail-tab-panel report-info-panel">
            <section class="info-section">
              <div class="section-heading">
                <h3 class="tab-panel-title">历史版本</h3>
              </div>
              <div class="version-list">
                <button
                  v-for="item in versionCards"
                  :key="item.row.id"
                  class="version-record"
                  :class="{ 'version-record--active': item.isCurrent }"
                  type="button"
                  @click="emit('selectVersion', item.row.id)"
                >
                  <span class="version-record-main">
                    <span class="version-record-title">
                      <strong>{{ item.versionLabel }}</strong>
                      <span>{{ item.createdAt }}</span>
                      <el-tag v-if="item.isLatest" type="success" size="small" round disable-transitions>最新</el-tag>
                    </span>
                    <span class="version-record-meta">
                      {{ item.templateName }} · {{ item.modelName }} · {{ item.materialCount }} 条素材
                    </span>
                  </span>
                  <el-tag v-if="item.isCurrent" type="success" size="small" round disable-transitions>当前版本</el-tag>
                </button>
              </div>
            </section>

            <section class="info-section">
              <div class="section-heading">
                <h3 class="tab-panel-title">基本信息</h3>
              </div>
              <dl class="info-grid">
                <div v-for="item in infoItems" :key="item.label" class="info-card" :class="`info-card--${item.tone}`">
                  <span class="info-card-icon">
                    <el-icon><component :is="item.icon" /></el-icon>
                  </span>
                  <div class="info-card-copy">
                    <dt>{{ item.label }}</dt>
                    <dd>
                      <span>{{ item.value }}</span>
                      <small v-if="item.suffix">{{ item.suffix }}</small>
                    </dd>
                  </div>
                </div>
              </dl>
            </section>

            <section class="info-section">
              <div class="section-heading">
                <h3 class="tab-panel-title">素材概览</h3>
              </div>
              <div class="source-strip">
                <span
                  v-for="item in sourceCards"
                  :key="item.key"
                  class="source-card"
                  :class="`source-card--${item.tone}`"
                >
                  <span class="source-card-icon">
                    <el-icon><component :is="item.icon" /></el-icon>
                  </span>
                  <span class="source-card-copy">
                    <em>{{ item.label }}</em>
                    <strong>{{ sourceTotalLabel(item.value, item.total) }}</strong>
                  </span>
                  <span class="source-card-percent">{{ formatPercent(item.percent) }}</span>
                  <span class="source-card-progress">
                    <i :style="progressWidth(item.percent)" />
                  </span>
                </span>
              </div>
            </section>
          </div>
        </el-tab-pane>

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

        <el-tab-pane label="Prompt" name="prompt">
          <pre class="raw-block">{{ report.prompt_text || '暂无 Prompt' }}</pre>
        </el-tab-pane>

        <el-tab-pane label="素材明细" name="materials">
          <pre class="raw-block">{{ report.material_snapshot_json || report.material_summary || '暂无素材快照' }}</pre>
        </el-tab-pane>

      </el-tabs>
    </template>

    <el-empty v-else description="请选择一天的历史日报查看详情" />
  </section>
</template>

<style scoped>
.history-detail-card {
  min-width: 0;
  min-height: 0;
  display: block;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
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
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
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
  color: #53627a;
  font-size: 12px;
  font-weight: 650;
}

.info-card dd {
  display: flex;
  align-items: baseline;
  gap: 4px;
  overflow: hidden;
  margin-top: 4px;
  color: #0f1d35;
  font-size: 15px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-card dd span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.info-card dd small {
  flex: 0 0 auto;
  color: #526070;
  font-size: 12px;
  font-weight: 650;
}

.info-card-icon,
.source-card-icon {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 8px;
}

.info-card-icon {
  width: 34px;
  height: 34px;
}

.info-card-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.info-card-copy {
  min-width: 0;
}

.info-card--blue .info-card-icon,
.source-card--blue .source-card-icon {
  background: #edf5ff;
  color: #2f80ed;
}

.info-card--indigo .info-card-icon {
  background: #eef2ff;
  color: #4f6df5;
}

.info-card--cyan .info-card-icon {
  background: #ecfeff;
  color: #0891b2;
}

.info-card--orange .info-card-icon,
.source-card--orange .source-card-icon {
  background: #fff7ed;
  color: #ea7b17;
}

.info-card--green .info-card-icon,
.source-card--green .source-card-icon {
  background: #edfdf5;
  color: #16934f;
}

.info-card--slate .info-card-icon {
  background: #f3f5f8;
  color: #667085;
}

.source-strip {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  overflow: visible;
}

.source-card {
  position: relative;
  min-width: 0;
  min-height: 76px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 9px;
  padding: 12px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  background: #fff;
}

.source-card-icon {
  width: 32px;
  height: 32px;
}

.source-card-icon :deep(svg) {
  width: 17px;
  height: 17px;
}

.source-card-copy {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.source-card em {
  overflow: hidden;
  color: #53627a;
  font-size: 12px;
  font-weight: 650;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-card strong {
  color: #0f1d35;
  font-size: 15px;
  font-weight: 850;
  white-space: nowrap;
}

.source-card-percent {
  align-self: end;
  color: #526070;
  font-size: 12px;
  font-weight: 720;
}

.source-card-progress {
  grid-column: 1 / -1;
  align-self: end;
  width: 100%;
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: #e8edf4;
}

.source-card-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.source-card--blue .source-card-progress i {
  background: #2f80ed;
}

.source-card--green .source-card-progress i {
  background: #16934f;
}

.source-card--orange .source-card-progress i {
  background: #ea7b17;
}

.source-card--purple .source-card-icon {
  background: #f5efff;
  color: #7c3aed;
}

.source-card--purple .source-card-progress i {
  background: #7c3aed;
}

.detail-tabs {
  height: 100%;
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

.detail-tab-panel,
.markdown-preview,
.raw-block {
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 16px;
  border-radius: 8px;
  background: #fbfdff;
}

.detail-tab-panel {
  display: grid;
  align-content: start;
  gap: 12px;
}

.report-info-panel {
  overflow: auto;
}

.info-section {
  min-width: 0;
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 8px;
    border: 1px solid #e3ebf6;
}

.tab-panel-title {
  margin: 0;
  color: #0f1d35;
  font-size: 15px;
  font-weight: 840;
}

.section-heading p {
  margin: 0;
}

.section-heading p {
  margin-top: 4px;
  color: #526070;
  font-size: 12px;
}

.section-heading {
  min-width: 0;
}

.version-list {
  min-width: 0;
  display: grid;
  gap: 8px;
}

.version-record {
  min-width: 0;
  width: 100%;
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  background: #fbfdff;
  color: #526070;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease;
}

.version-record:hover,
.version-record--active {
  border-color: #9ec5ff;
  background: #f4f9ff;
}

.version-record-main {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.version-record-title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #526070;
  font-size: 13px;
  white-space: nowrap;
}

.version-record-title strong {
  color: #0f1d35;
  font-size: 15px;
  font-weight: 820;
}

.version-record-title span,
.version-record-meta {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.version-record-meta {
  color: #667085;
  font-size: 12px;
  white-space: nowrap;
}

.version-record > .el-tag {
  flex: 0 0 auto;
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

@media (max-width: 1280px) {
  .info-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .source-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .info-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .source-strip {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
