<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, Delete } from '@element-plus/icons-vue'

import type { AnyRecord, SourceType } from '../../api/types'
import CategoryTag from './CategoryTag.vue'
import SensitiveTag from './SensitiveTag.vue'
import SourceBadge from './SourceBadge.vue'
import type { DetailSavePayload } from './types'
import { CATEGORY_OPTIONS, browserRecordTypeLabel, formatDateTime, formatDuration, recordId, recordPreview, recordSource, recordTitle } from './types'

const props = defineProps<{
  modelValue: boolean
  record: AnyRecord | null
  loading: boolean
  saving: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [payload: DetailSavePayload]
  delete: [sourceType: SourceType, id: number]
}>()

const draft = reactive({
  category: '',
  note: '',
  importance: 0,
  selected: false,
  sensitive: false,
  sensitivityReason: ''
})

const sourceType = computed(() => (props.record ? recordSource(props.record) : 'app'))
const sourceId = computed(() => (props.record ? recordId(props.record) : 0))
const drawerTitle = computed(() => {
  if (!props.record) {
    return '记录详情'
  }
  return `${sourceLabelText(sourceType.value)}详情`
})

const baseFields = computed(() => {
  const row = props.record
  if (!row) {
    return []
  }
  if (sourceType.value === 'app') {
    return [
      ['应用名称', row.app_name],
      ['进程名', row.process_name],
      ['窗口标题', row.window_title],
      ['可执行文件', row.exe_path],
      ['开始时间', formatDateTime(row.start_time)],
      ['结束时间', formatDateTime(row.end_time)],
      ['持续时长', formatDuration(row.duration_sec)],
      ['活跃时长', formatDuration(row.active_duration_sec)]
    ]
  }
  if (sourceType.value === 'browser') {
    return [
      ['记录类型', browserRecordTypeLabel(row.record_type)],
      ['原始来源', row.origin_source_type],
      ['浏览器', row.browser],
      ['配置', row.profile_name],
      ['发生时间', formatDateTime(row.visit_time || row.timestamp || row.start_time)],
      ['标题', row.title],
      ['域名', row.domain],
      ['搜索引擎', row.search_engine],
      ['搜索词', row.search_query],
      ['停留时长', formatDuration(row.duration_sec)],
      ['URL', row.url]
    ]
  }
  if (sourceType.value === 'clipboard') {
    return [
      ['首次出现', formatDateTime(row.first_seen_at)],
      ['最后出现', formatDateTime(row.last_seen_at)],
      ['字符数', row.char_count],
      ['出现次数', row.seen_count],
      ['内容哈希', row.content_hash]
    ]
  }
  if (sourceType.value === 'browser_event') {
    return [
      ['事件类型', row.event_type],
      ['发生时间', formatDateTime(row.timestamp)],
      ['标题', row.title],
      ['域名', row.domain],
      ['搜索引擎', row.search_engine],
      ['搜索词', row.search_query],
      ['停留时长', formatDuration(row.duration_sec)],
      ['URL', row.url],
      ['来源', row.source]
    ]
  }
  return [
    ['平台', row.platform],
    ['来源', row.source],
    ['页面标题', row.page_title],
    ['提问时间', formatDateTime(row.timestamp)],
    ['字符数', row.char_count],
    ['会话 URL', row.conversation_url]
  ]
})
const aggregateItems = computed(() => {
  const rows = props.record?.aggregate_items
  return Array.isArray(rows) ? rows as AnyRecord[] : []
})

function sourceLabelText(value: SourceType): string {
  return {
    app: '应用记录',
    browser: '浏览记录',
    clipboard: '剪切板记录',
    ai_prompt: 'AI 提问',
    browser_event: '浏览器事件'
  }[value]
}

function closeDrawer(): void {
  emit('update:modelValue', false)
}

function save(): void {
  if (!props.record) {
    return
  }
  emit('save', {
    sourceType: sourceType.value,
    id: sourceId.value,
    entryKey: typeof props.record.entry_key === 'string' ? props.record.entry_key : null,
    category: draft.category || null,
    note: draft.note || null,
    importance: draft.importance,
    sensitive: draft.sensitive,
    sensitivityReason: draft.sensitivityReason || null,
    selected: draft.selected
  })
}

async function copyContent(): Promise<void> {
  const text = String(props.record?.content || props.record?.prompt_text || recordPreview(props.record || {}) || '')
  if (!text) {
    return
  }
  await navigator.clipboard?.writeText(text)
  ElMessage.success('内容已复制')
}

watch(
  () => props.record,
  (row) => {
    const annotation = row?.annotation as AnyRecord | null | undefined
    draft.category = String(row?.category || annotation?.category || '其他')
    draft.note = String(row?.note || annotation?.note || '')
    draft.importance = Number(row?.importance || annotation?.importance || 0)
    draft.selected = Boolean(row?.is_selected ?? annotation?.is_selected_override ?? false)
    draft.sensitive = Boolean(row?.is_sensitive)
    draft.sensitivityReason = String(row?.sensitivity_reason || annotation?.sensitivity_reason_override || '')
  },
  { immediate: true }
)
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    class="record-detail-drawer"
    size="min(720px, 92vw)"
    :with-header="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="loading" class="drawer-loading">
      <header class="drawer-header">
        <div class="drawer-title-block">
          <h2 class="drawer-title">记录详情</h2>
          <p class="drawer-subtitle">正在加载...</p>
        </div>
        <el-button :icon="Close" circle @click="closeDrawer" />
      </header>
      <main class="drawer-body">
        <el-skeleton :rows="12" animated />
      </main>
    </div>

    <div v-else-if="record" class="drawer-shell">
      <header class="drawer-header">
        <div class="drawer-title-block">
          <SourceBadge :source-type="sourceType" />
          <h2 class="drawer-title">{{ drawerTitle }}</h2>
          <p class="drawer-subtitle">{{ recordTitle(record) }}</p>
        </div>
        <el-button :icon="Close" circle @click="closeDrawer" />
      </header>

      <main class="drawer-body">
        <section class="detail-section">
          <div class="summary-line">
            <CategoryTag :category="draft.category" />
            <SensitiveTag :sensitive="draft.sensitive" />
          </div>
          <p class="record-preview">{{ recordPreview(record) || '暂无内容预览' }}</p>
        </section>

        <section class="detail-section">
          <h3 class="section-title">基础信息</h3>
          <dl class="field-list">
            <template v-for="field in baseFields" :key="field[0]">
              <dt>{{ field[0] }}</dt>
              <dd>{{ field[1] || '-' }}</dd>
            </template>
          </dl>
        </section>

        <section v-if="aggregateItems.length" class="detail-section">
          <h3 class="section-title">聚合明细</h3>
          <div class="aggregate-list">
            <article v-for="row in aggregateItems" :key="String(row.id)" class="aggregate-row">
              <span class="aggregate-time">
                {{ formatDateTime(row.start_time).slice(11, 16) }} - {{ formatDateTime(row.end_time).slice(11, 16) }}
              </span>
              <strong>{{ row.window_title || row.app_name || row.process_name || '-' }}</strong>
              <span>{{ formatDuration(row.active_duration_sec || row.duration_sec) }}</span>
            </article>
          </div>
        </section>

        <section v-if="record.content || record.prompt_text" class="detail-section">
          <h3 class="section-title">内容详情</h3>
          <el-input
            :model-value="String(record.content || record.prompt_text || '')"
            type="textarea"
            :rows="8"
            readonly
          />
          <el-button class="copy-button" @click="copyContent">
            复制内容
          </el-button>
        </section>

        <section class="detail-section">
          <h3 class="section-title">治理信息</h3>
          <div class="governance-grid">
            <label class="drawer-field">
              <span>分类</span>
              <el-select v-model="draft.category" filterable>
                <el-option v-for="item in CATEGORY_OPTIONS" :key="item" :label="item" :value="item" />
              </el-select>
            </label>
            <label class="drawer-field">
              <span>重要性</span>
              <el-input-number v-model="draft.importance" :min="0" :max="100" />
            </label>
            <label class="drawer-field drawer-field--switch">
              <span>纳入日报</span>
              <el-switch v-model="draft.selected" active-text="纳入" inactive-text="排除" />
            </label>
            <label class="drawer-field drawer-field--switch">
              <span>敏感状态</span>
              <el-switch v-model="draft.sensitive" active-text="敏感" inactive-text="非敏感" />
            </label>
            <label class="drawer-field drawer-field--full">
              <span>敏感原因</span>
              <el-input v-model="draft.sensitivityReason" clearable placeholder="可选" />
            </label>
            <label class="drawer-field drawer-field--full">
              <span>备注</span>
              <el-input v-model="draft.note" type="textarea" :rows="4" placeholder="记录治理备注" />
            </label>
          </div>
        </section>

        <section class="detail-section">
          <h3 class="section-title">系统字段</h3>
          <dl class="field-list">
            <dt>来源类型</dt>
            <dd>{{ sourceType }}</dd>
            <dt>记录类型</dt>
            <dd>{{ browserRecordTypeLabel(record.record_type) }}</dd>
            <dt>entry_key</dt>
            <dd>{{ record.entry_key || '-' }}</dd>
            <dt>原始来源</dt>
            <dd>{{ record.origin_source_type || '-' }}</dd>
            <dt>原始 ID</dt>
            <dd>{{ record.origin_source_id || '-' }}</dd>
            <dt>记录 ID</dt>
            <dd>{{ sourceId }}</dd>
            <dt>创建时间</dt>
            <dd>{{ formatDateTime(record.created_at) }}</dd>
            <dt>更新时间</dt>
            <dd>{{ formatDateTime(record.updated_at) }}</dd>
          </dl>
        </section>
      </main>

      <footer class="drawer-footer">
        <el-button @click="closeDrawer">
          取消
        </el-button>
        <el-button :icon="Delete" type="danger" plain @click="$emit('delete', sourceType, sourceId)">
          删除记录
        </el-button>
        <el-button type="primary" :loading="saving" @click="save">
          保存修改
        </el-button>
      </footer>
    </div>

    <div v-else class="drawer-loading">
      <header class="drawer-header">
        <div class="drawer-title-block">
          <h2 class="drawer-title">记录详情</h2>
          <p class="drawer-subtitle">暂无可显示的记录</p>
        </div>
        <el-button :icon="Close" circle @click="closeDrawer" />
      </header>
      <main class="drawer-body">
        <el-empty description="暂无记录详情" />
      </main>
    </div>
  </el-drawer>
</template>

<style scoped>
:deep(.record-detail-drawer .el-drawer__body) {
  min-width: 0;
  overflow: hidden;
}

.drawer-shell,
.drawer-loading {
  display: grid;
  height: 100%;
  min-width: 0;
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.drawer-header,
.drawer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid #e4ebf5;
}

.drawer-footer {
  border-top: 1px solid #e4ebf5;
  border-bottom: 0;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.drawer-title-block {
  min-width: 0;
}

.drawer-title {
  margin: 10px 0 0;
  color: #172033;
  font-size: 20px;
  font-weight: 850;
}

.drawer-subtitle {
  margin: 6px 0 0;
  overflow: hidden;
  color: #5f6b7b;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-body {
  display: grid;
  gap: 14px;
  min-height: 0;
  overflow: auto;
  padding: 16px 20px;
  background: #f8fbff;
}

.detail-section {
  padding: 14px;
  border: 1px solid #dfe8f5;
  border-radius: 12px;
  background: #fff;
}

.summary-line {
  display: flex;
  gap: 8px;
}

.record-preview {
  margin: 12px 0 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: #3f4c5d;
  font-size: 13px;
  line-height: 1.6;
}

.section-title {
  margin: 0 0 12px;
  color: #1e2a3b;
  font-size: 14px;
  font-weight: 820;
}

.aggregate-list {
  display: grid;
  gap: 8px;
}

.aggregate-row {
  min-width: 0;
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) 70px;
  gap: 10px;
  align-items: center;
  padding: 9px 10px;
  border: 1px solid #e6edf7;
  border-radius: 8px;
  background: #f8fafc;
  color: #536174;
  font-size: 12px;
}

.aggregate-row strong {
  min-width: 0;
  overflow: hidden;
  color: #1e2a3b;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aggregate-time {
  font-variant-numeric: tabular-nums;
}

.field-list {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 9px 12px;
  margin: 0;
  font-size: 13px;
}

.field-list dt {
  color: #718096;
}

.field-list dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: #263347;
}

.copy-button {
  margin-top: 10px;
}

.governance-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(130px, 0.42fr);
  gap: 12px;
}

.drawer-field {
  display: grid;
  gap: 7px;
  color: #526070;
  font-size: 12px;
  font-weight: 750;
}

.drawer-field--full {
  grid-column: 1 / -1;
}

.drawer-field--switch {
  align-content: end;
}

@media (max-width: 620px) {
  .governance-grid,
  .field-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .drawer-footer {
    justify-content: flex-start;
  }
}
</style>
