<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, MagicStick, Warning } from '@element-plus/icons-vue'

import type { MaterialCandidate, MaterialSummary, ReportTemplate } from '../../types/reportWorkbench'

const props = defineProps<{
  summary: MaterialSummary
  selectedMaterials: MaterialCandidate[]
  selectedTemplate: ReportTemplate | undefined
  outputFocus: string[]
  extraRequirements: string
  promptDirty: boolean
  promptText: string
  generating: boolean
  canGenerate: boolean
  showActions?: boolean
}>()

const emit = defineEmits<{
  editMaterials: []
  editPrompt: []
  buildPrompt: []
  generate: []
}>()

const categoryCounts = computed(() => {
  const counts = new Map<string, number>()
  for (const item of props.selectedMaterials) {
    const key = item.category || '其他'
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return [...counts.entries()].map(([label, count]) => ({ label, count })).slice(0, 8)
})

const checks = computed(() => [
  {
    label: props.summary.sensitive_excluded_count > 0 ? '存在已排除的敏感素材' : '未发现敏感内容',
    tone: props.summary.sensitive_excluded_count > 0 ? 'warning' : 'success'
  },
  {
    label: categoryCounts.value.length > 0 ? '素材已按分类组织' : '未发现已分类素材',
    tone: categoryCounts.value.length > 0 ? 'success' : 'warning'
  },
  {
    label: props.summary.estimated_prompt_chars > 50000 ? '预计内容较长' : '未发现过长素材',
    tone: props.summary.estimated_prompt_chars > 50000 ? 'warning' : 'success'
  },
  {
    label: props.promptDirty || !props.promptText ? 'Prompt 需要重新构建' : 'Prompt 已构建',
    tone: props.promptDirty || !props.promptText ? 'warning' : 'success'
  }
])
</script>

<template>
  <section class="workbench-card submit-summary-card">
    <header class="card-header">
      <div>
        <h2 class="card-title">提交摘要</h2>
        <p class="card-subtitle">生成前快速检查素材、模板和 Prompt 状态</p>
      </div>
    </header>

    <div class="summary-section">
      <h3>选择统计</h3>
      <dl>
        <div>
          <dt>已选素材</dt>
          <dd>{{ summary.selected_count.toLocaleString() }} 条</dd>
        </div>
        <div>
          <dt>敏感已排除</dt>
          <dd>{{ summary.sensitive_excluded_count.toLocaleString() }} 条</dd>
        </div>
        <div>
          <dt>待确认素材</dt>
          <dd>{{ summary.pending_count.toLocaleString() }} 条</dd>
        </div>
        <div>
          <dt>预计发送字数</dt>
          <dd>{{ summary.estimated_prompt_chars.toLocaleString() }} 字</dd>
        </div>
      </dl>
    </div>

    <div class="summary-section">
      <h3>素材分类分布</h3>
      <ul class="category-list">
        <li v-for="item in categoryCounts" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.count }} 条</strong>
        </li>
        <li v-if="!categoryCounts.length">
          <span>暂无已选素材分类</span>
          <strong>0 条</strong>
        </li>
      </ul>
    </div>

    <div class="summary-section">
      <h3>Prompt 信息</h3>
      <dl>
        <div>
          <dt>模板</dt>
          <dd>{{ selectedTemplate?.name || '未选择模板' }}</dd>
        </div>
        <div>
          <dt>输出重点</dt>
          <dd>{{ outputFocus.length }} 项</dd>
        </div>
        <div>
          <dt>补充要求</dt>
          <dd>{{ extraRequirements.trim().length }} 字</dd>
        </div>
      </dl>
    </div>

    <div class="summary-section">
      <h3>快速检查</h3>
      <ul class="check-list">
        <li v-for="item in checks" :key="item.label" :class="`check-item--${item.tone}`">
          <CircleCheck v-if="item.tone === 'success'" />
          <Warning v-else />
          <span>{{ item.label }}</span>
        </li>
      </ul>
    </div>

    <footer v-if="showActions !== false" class="summary-actions">
      <el-button plain @click="emit('editMaterials')">返回修改素材</el-button>
      <el-button plain @click="emit('editPrompt')">返回修改 Prompt</el-button>
      <el-button v-if="promptDirty || !promptText" :icon="MagicStick" @click="emit('buildPrompt')">
        重新构建 Prompt
      </el-button>
      <el-button type="primary" :loading="generating" :disabled="!canGenerate" @click="emit('generate')">
        生成日报
      </el-button>
    </footer>
  </section>
</template>

<style scoped>
.submit-summary-card {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto auto minmax(86px, 1fr) auto;
  gap: 9px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  margin: 0;
  color: #172033;
  font-size: 16px;
  font-weight: 840;
}

.card-subtitle {
  margin: 4px 0 0;
  color: #667085;
  font-size: 12px;
}

.summary-section {
  min-width: 0;
  display: grid;
  gap: 7px;
  padding: 10px;
  border: 1px solid #e3ebf6;
  border-radius: 12px;
  background: #fbfdff;
}

.summary-section h3 {
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 840;
}

.summary-section dl,
.category-list,
.check-list {
  display: grid;
  gap: 6px;
  padding: 0;
  margin: 0;
}

.summary-section:first-of-type dl {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.summary-section dl div,
.category-list li {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 20px;
}

.summary-section dt,
.category-list span {
  color: #667085;
  font-size: 12px;
}

.summary-section dd,
.category-list strong {
  margin: 0;
  color: #172033;
  font-size: 12px;
  font-weight: 820;
  text-align: right;
}

.category-list,
.check-list {
  list-style: none;
}

.category-list {
  max-height: 74px;
  overflow: auto;
}

.check-list {
  overflow: auto;
}

.check-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #526070;
  font-size: 12px;
  min-height: 20px;
}

.check-list svg {
  width: 15px;
  height: 15px;
}

.check-item--success svg {
  color: #16a34a;
}

.check-item--warning svg {
  color: #f59e0b;
}

.summary-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
