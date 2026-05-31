<script setup lang="ts">
import { ChatDotRound, CopyDocument, Monitor, Link } from '@element-plus/icons-vue'

import type { SourceType } from '../../api/types'
import { sourceLabel } from './types'

const props = withDefaults(defineProps<{
  sourceType: SourceType
  iconOnly?: boolean
}>(), {
  iconOnly: false
})

const iconMap = {
  app: Monitor,
  browser: Link,
  clipboard: CopyDocument,
  ai_prompt: ChatDotRound
}
</script>

<template>
  <span class="source-badge" :class="[`source-badge--${props.sourceType}`, { 'source-badge--icon-only': props.iconOnly }]">
    <el-icon class="source-badge-icon">
      <component :is="iconMap[props.sourceType]" />
    </el-icon>
    <span v-if="!props.iconOnly">{{ sourceLabel(props.sourceType) }}</span>
  </span>
</template>

<style scoped>
.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  height: 26px;
  padding: 0 9px;
  border: 1px solid #dbe7f7;
  border-radius: 999px;
  background: #f8fbff;
  color: #315f9f;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.source-badge--app {
  color: var(--datacenter-blue, #409eff);
  background: #ecf5ff;
  border-color: #d9ecff;
}

.source-badge--browser {
  color: var(--datacenter-green, #67c23a);
  background: #f0f9eb;
  border-color: #e1f3d8;
}

.source-badge--clipboard {
  color: var(--datacenter-orange, #e6a23c);
  background: #fdf6ec;
  border-color: #faecd8;
}

.source-badge--ai_prompt {
  color: var(--datacenter-purple, #f56c6c);
  background: #fef0f0;
  border-color: #fde2e2;
}

.source-badge-icon {
  font-size: 14px;
}

.source-badge--icon-only {
  width: 36px;
  height: 36px;
  justify-content: center;
  padding: 0;
  border-radius: 8px;
}

.source-badge--icon-only .source-badge-icon {
  font-size: 18px;
}
</style>
