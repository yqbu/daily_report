<script setup lang="ts">
import { computed } from 'vue'
import { ChatDotRound, CopyDocument, Link, Monitor, View } from '@element-plus/icons-vue'

import type { MaterialCandidate } from '../../types/reportWorkbench'

const props = defineProps<{
  items: MaterialCandidate[]
  loading: boolean
  hasMore: boolean
}>()

const emit = defineEmits<{
  toggle: [item: MaterialCandidate, selected: boolean]
  detail: [item: MaterialCandidate]
  loadMore: []
}>()

const sourceMeta = computed(() => ({
  app: { label: '前台应用', icon: Monitor, className: 'source-app' },
  browser: { label: '浏览器历史', icon: Link, className: 'source-browser' },
  clipboard: { label: '剪切板', icon: CopyDocument, className: 'source-clipboard' },
  ai_prompt: { label: 'AI 提问', icon: ChatDotRound, className: 'source-ai' }
}))
</script>

<template>
  <div class="material-list">
    <article
      v-for="item in items"
      :key="`${item.source_type}:${item.source_id}`"
      class="material-row"
      :class="{ 'material-row--sensitive': item.is_sensitive }"
      @click="emit('detail', item)"
    >
      <el-checkbox
        :model-value="item.is_selected"
        class="material-check"
        @click.stop
        @update:model-value="emit('toggle', item, Boolean($event))"
      />

      <div class="source-icon" :class="sourceMeta[item.source_type].className">
        <el-icon><component :is="sourceMeta[item.source_type].icon" /></el-icon>
      </div>

      <div class="material-main">
        <div class="material-title-line">
          <el-tag size="small" effect="plain">{{ sourceMeta[item.source_type].label }}</el-tag>
          <strong class="material-title">{{ item.title }}</strong>
          <el-tag v-if="item.category" size="small" type="info" effect="light">{{ item.category }}</el-tag>
          <el-tag v-if="item.is_sensitive" size="small" type="danger" effect="light">
            敏感
          </el-tag>
        </div>
        <p class="material-summary">{{ item.summary }}</p>
        <div class="material-meta">
          <span>{{ item.time_range || '-' }}</span>
          <span v-if="item.importance">重要性 {{ item.importance }}</span>
          <span v-if="item.sensitivity_reason">{{ item.sensitivity_reason }}</span>
        </div>
      </div>

      <el-button :icon="View" circle text title="查看详情" @click.stop="emit('detail', item)" />
    </article>

    <div v-if="!items.length && !loading" class="material-empty">
      当前日期暂无可用素材，请确认采集服务是否运行，或切换日期。
    </div>

    <div class="material-list-footer">
      <el-button v-if="hasMore" :loading="loading" @click="emit('loadMore')">
        加载更多
      </el-button>
      <span v-else-if="items.length" class="footer-text">已加载全部素材</span>
    </div>
  </div>
</template>

<style scoped>
.material-list {
  height: 100%;
  max-height: 100%;
  display: grid;
  grid-auto-rows: max-content;
  gap: 10px;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-gutter: stable;
}

.material-row {
  min-width: 0;
  display: grid;
  grid-template-columns: auto 34px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid #e3ebf6;
  border-radius: 10px;
  background: #fbfdff;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background 160ms ease,
    transform 160ms ease;
}

.material-row:hover {
  border-color: #c9dcff;
  background: #f4f8ff;
  transform: translateY(-1px);
}

.material-row--sensitive {
  border-color: #ffd9d9;
  background: #fffafa;
}

.material-check {
  margin-top: 4px;
}

.source-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: #eef4ff;
  color: #2563eb;
}

.source-browser {
  background: #eefaf2;
  color: #16a34a;
}

.source-clipboard {
  background: #fff7ed;
  color: #ea580c;
}

.source-ai {
  background: #f3e8ff;
  color: #7c3aed;
}

.material-main {
  min-width: 0;
}

.material-title-line {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.material-title {
  min-width: 0;
  overflow: hidden;
  color: #1e2a3b;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-summary {
  margin: 7px 0 0;
  color: #526070;
  font-size: 12px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.material-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  color: #8792a2;
  font-size: 12px;
}

.material-empty {
  min-height: 160px;
  display: grid;
  place-items: center;
  padding: 24px;
  border: 1px dashed #d9e4f2;
  border-radius: 12px;
  color: #667085;
  text-align: center;
  background: #fbfdff;
}

.material-list-footer {
  display: flex;
  justify-content: center;
  padding: 4px 0 0;
}

.footer-text {
  color: #98a2b3;
  font-size: 12px;
}

@media (max-width: 620px) {
  .material-row {
    grid-template-columns: auto 34px minmax(0, 1fr);
  }

  .material-row > .el-button {
    grid-column: 3;
    justify-self: flex-start;
  }
}
</style>
