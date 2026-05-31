<script setup lang="ts">
import { CopyDocument } from '@element-plus/icons-vue'

defineProps<{
  modelValue: boolean
  promptText: string
  templateName: string
  selectedMaterialCount: number
  extraRequirements: string
  warnings: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  copy: [text: string]
}>()
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    size="min(760px, 92vw)"
    title="Prompt 预览"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="prompt-preview-shell">
      <section class="prompt-section">
        <h3>系统提示词</h3>
        <p>你是一名严谨的个人工作日报写作助手。请只根据本地采集并人工筛选后的素材生成中文 Markdown 日报。</p>
      </section>

      <section class="prompt-section">
        <h3>模板与素材</h3>
        <dl>
          <dt>模板</dt>
          <dd>{{ templateName }}</dd>
          <dt>选中素材</dt>
          <dd>{{ selectedMaterialCount }} 条</dd>
        </dl>
      </section>

      <section class="prompt-section">
        <h3>补充要求</h3>
        <p>{{ extraRequirements || '无补充要求' }}</p>
      </section>

      <el-alert
        v-for="warning in warnings"
        :key="warning"
        type="warning"
        show-icon
        :closable="false"
        :title="warning"
      />

      <section class="prompt-section prompt-section--full">
        <div class="prompt-final-header">
          <h3>最终发送给模型的 Prompt</h3>
          <el-button :icon="CopyDocument" :disabled="!promptText" @click="emit('copy', promptText)">复制</el-button>
        </div>
        <el-input :model-value="promptText" type="textarea" :rows="20" readonly resize="none" placeholder="尚未构建 Prompt" />
      </section>
    </div>
  </el-drawer>
</template>

<style scoped>
.prompt-preview-shell {
  display: grid;
  gap: 12px;
}

.prompt-section {
  min-width: 0;
  padding: 14px;
  border: 1px solid #dfe8f5;
  border-radius: 12px;
  background: #fbfdff;
}

.prompt-section h3 {
  margin: 0 0 8px;
  color: #172033;
  font-size: 14px;
  font-weight: 840;
}

.prompt-section p {
  margin: 0;
  color: #526070;
  line-height: 1.65;
  white-space: pre-wrap;
}

.prompt-section dl {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  margin: 0;
  color: #526070;
}

.prompt-section dd {
  margin: 0;
  color: #172033;
}

.prompt-final-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
