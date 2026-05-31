<script setup lang="ts">
import { computed } from 'vue'
import { CopyDocument, Delete, Download, MagicStick, View } from '@element-plus/icons-vue'

import type { ReportHistoryRow } from '../../types/reportWorkbench'

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

const infoItems = computed(() => {
  const report = props.report
  if (!report) {
    return []
  }
  const counts = report.source_counts ?? {}
  const materialCount = ['app', 'browser', 'clipboard', 'ai_prompt'].reduce((total, key) => total + Number(counts[key] || 0), 0)
  return [
    ['生成日期', report.date],
    ['生成时间', report.created_at?.replace('T', ' ').slice(0, 19) || '-'],
    ['模板名称', report.template_name || '-'],
    ['模型名称', report.model_name || '-'],
    ['字数', String((report.report_markdown || '').length)],
    ['使用素材数', String(materialCount)],
    ['敏感排除数', String(counts.sensitive_excluded_count || 0)]
  ]
})
</script>

<template>
  <section v-loading="loading" class="history-detail-card">
    <template v-if="report">
      <header class="detail-header">
        <div>
          <h2 class="detail-title">{{ report.date }} 日报</h2>
          <p class="detail-subtitle">{{ report.template_name }} · {{ report.model_name }}</p>
        </div>
        <div class="detail-actions">
          <el-button :icon="CopyDocument" @click="emit('copy', report.report_markdown || '')">复制 Markdown</el-button>
          <el-button :icon="Download" @click="emit('export', report)">导出 .md</el-button>
          <el-button :icon="View" @click="emit('viewPrompt', report.prompt_text || '')">查看 Prompt</el-button>
          <el-button :icon="MagicStick" type="primary" plain @click="emit('regenerate', report)">
            基于该日报重新生成
          </el-button>
          <el-button :icon="Delete" type="danger" plain @click="emit('delete', report.id)">删除日报</el-button>
        </div>
      </header>

      <dl class="info-grid">
        <template v-for="item in infoItems" :key="item[0]">
          <dt>{{ item[0] }}</dt>
          <dd>{{ item[1] }}</dd>
        </template>
      </dl>

      <div class="report-preview">
        <pre>{{ report.report_markdown || '暂无日报正文' }}</pre>
      </div>
    </template>

    <el-empty v-else description="请选择一篇历史日报查看详情。" />
  </section>
</template>

<style scoped>
.history-detail-card {
  min-width: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 12px;
  padding: 16px;
  border: 1px solid #dfe8f5;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 31, 61, 0.04);
}

.detail-header {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.detail-title {
  margin: 0;
  color: #172033;
  font-size: 16px;
  font-weight: 840;
}

.detail-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}

.detail-actions {
  min-width: 0;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}

.info-grid dt,
.info-grid dd {
  margin: 0;
  padding: 8px 10px;
  border: 1px solid #e3ebf6;
  background: #f8fbff;
}

.info-grid dt {
  border-radius: 9px 9px 0 0;
  color: #667085;
  font-size: 12px;
}

.info-grid dd {
  margin-top: -8px;
  border-top: 0;
  border-radius: 0 0 9px 9px;
  color: #172033;
  font-weight: 760;
}

.report-preview {
  min-height: 320px;
  overflow: auto;
  padding: 16px;
  border: 1px solid #e3ebf6;
  border-radius: 12px;
  background: #fbfdff;
}

.report-preview pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: #344054;
  font: inherit;
  line-height: 1.7;
}

@media (max-width: 1020px) {
  .detail-header {
    flex-direction: column;
  }

  .detail-actions {
    justify-content: flex-start;
  }

  .info-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .info-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
