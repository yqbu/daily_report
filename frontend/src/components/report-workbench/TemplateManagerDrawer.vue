<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { CopyDocument, Delete, Plus, Star } from '@element-plus/icons-vue'

import type { ReportTemplate } from '../../types/reportWorkbench'

const props = defineProps<{
  modelValue: boolean
  templates: ReportTemplate[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [template: ReportTemplate]
  delete: [id: string]
  setDefault: [id: string]
}>()

const draft = reactive<ReportTemplate>({
  id: '',
  name: '',
  description: '',
  content: '',
  outputStructure: '',
  builtin: false,
  isDefault: false
})

const variables = [
  '{{date}}',
  '{{selected_material_count}}',
  '{{app_summary}}',
  '{{browser_summary}}',
  '{{clipboard_summary}}',
  '{{ai_prompt_summary}}',
  '{{category_summary}}',
  '{{extra_requirements}}'
]

const selectedTemplate = computed(() => props.templates.find((item) => item.id === draft.id) ?? null)

function selectTemplate(template: ReportTemplate): void {
  Object.assign(draft, { ...template })
}

function createTemplate(): void {
  Object.assign(draft, {
    id: `custom_${Date.now()}`,
    name: '新建模板',
    description: '',
    content: '## 今日工作概述\n\n## 主要工作内容\n\n## 明日计划',
    outputStructure: 'Markdown 正文',
    builtin: false,
    isDefault: false
  })
}

function duplicateTemplate(): void {
  Object.assign(draft, {
    ...draft,
    id: `custom_${Date.now()}`,
    name: `${draft.name || '模板'} 副本`,
    builtin: false,
    isDefault: false
  })
}

function insertVariable(variable: string): void {
  draft.content = `${draft.content}${draft.content.endsWith('\n') ? '' : '\n'}${variable}`
}

function saveTemplate(): void {
  emit('save', { ...draft, builtin: Boolean(selectedTemplate.value?.builtin && selectedTemplate.value.id === draft.id) })
}

watch(
  () => props.modelValue,
  (open) => {
    if (open && props.templates.length) {
      selectTemplate(props.templates.find((item) => item.isDefault) ?? props.templates[0])
    }
  }
)
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    size="min(720px, 92vw)"
    class="template-drawer"
    title="模板管理"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="template-shell">
      <aside class="template-list">
        <div class="template-list-actions">
          <el-button :icon="Plus" type="primary" plain @click="createTemplate">新建模板</el-button>
          <el-button :icon="CopyDocument" @click="duplicateTemplate">复制模板</el-button>
        </div>
        <button
          v-for="template in templates"
          :key="template.id"
          class="template-item"
          :class="{ 'template-item--active': template.id === draft.id }"
          type="button"
          @click="selectTemplate(template)"
        >
          <strong>{{ template.name }}</strong>
          <span>{{ template.description || '暂无说明' }}</span>
          <el-tag v-if="template.builtin" size="small">内置</el-tag>
          <el-tag v-if="template.isDefault" size="small" type="success">默认</el-tag>
        </button>
      </aside>

      <main class="template-editor">
        <label class="editor-field">
          <span>模板名称</span>
          <el-input v-model="draft.name" />
        </label>
        <label class="editor-field">
          <span>模板说明</span>
          <el-input v-model="draft.description" />
        </label>
        <label class="editor-field">
          <span>模板内容</span>
          <el-input v-model="draft.content" type="textarea" :rows="9" resize="none" />
        </label>
        <label class="editor-field">
          <span>输出结构</span>
          <el-input v-model="draft.outputStructure" type="textarea" :rows="3" resize="none" />
        </label>

        <div class="variable-list">
          <span>可用变量</span>
          <el-tag v-for="variable in variables" :key="variable" class="variable-chip" @click="insertVariable(variable)">
            {{ variable }}
          </el-tag>
        </div>

        <footer class="template-footer">
          <el-button :icon="Star" @click="emit('setDefault', draft.id)">设为默认</el-button>
          <el-button :icon="Delete" type="danger" plain :disabled="draft.builtin" @click="emit('delete', draft.id)">
            删除模板
          </el-button>
          <el-button type="primary" @click="saveTemplate">保存模板</el-button>
        </footer>
      </main>
    </div>
  </el-drawer>
</template>

<style scoped>
.template-shell {
  min-height: 0;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 14px;
}

.template-list,
.template-editor {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 10px;
}

.template-list-actions,
.template-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.template-item {
  min-width: 0;
  display: grid;
  gap: 6px;
  padding: 11px;
  border: 1px solid #e3ebf6;
  border-radius: 10px;
  color: #526070;
  text-align: left;
  background: #fbfdff;
  cursor: pointer;
}

.template-item--active,
.template-item:hover {
  border-color: #9ec5ff;
  background: #f1f7ff;
}

.template-item strong {
  color: #172033;
}

.editor-field {
  display: grid;
  gap: 7px;
  color: #526070;
  font-size: 12px;
  font-weight: 800;
}

.variable-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: #526070;
  font-size: 12px;
  font-weight: 800;
}

.variable-chip {
  cursor: pointer;
}

.template-footer {
  justify-content: flex-end;
  padding-top: 4px;
}

@media (max-width: 680px) {
  .template-shell {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
