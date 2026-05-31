<script setup lang="ts">
import { ElMessage } from 'element-plus'

import MaterialSelectionCard from './MaterialSelectionCard.vue'
import PromptConfigCard from './PromptConfigCard.vue'
import ReportResultPreviewCard from './ReportResultPreviewCard.vue'
import { useReportWorkbenchStore } from '../../stores/reportWorkbench'
import type { MaterialFilters, PromptOptions } from '../../types/reportWorkbench'

const store = useReportWorkbenchStore()

async function copyText(text: string): Promise<void> {
  if (!text) {
    return
  }
  await navigator.clipboard?.writeText(text)
  ElMessage.success('内容已复制')
}

async function buildPrompt(): Promise<void> {
  await store.buildCurrentPrompt(true)
  ElMessage.success('Prompt 已构建')
}

async function generateReport(): Promise<void> {
  try {
    await store.generateCurrentReport()
    ElMessage.success('日报已生成')
  } catch {
    ElMessage.error('日报生成失败，请检查模型配置或网络连接。')
  }
}

function updateMaterialFilters(filters: MaterialFilters): void {
  store.materialFilters.sourceTypes = filters.sourceTypes
  store.materialFilters.category = filters.category
  store.materialFilters.sensitive = filters.sensitive
  store.materialFilters.keyword = filters.keyword
  void store.loadMaterials(true)
}

function updatePromptOptions(options: PromptOptions): void {
  store.promptOptions.includeMaterialSummary = options.includeMaterialSummary
  store.promptOptions.includeTomorrowPlan = options.includeTomorrowPlan
  store.promptOptions.groupByCategory = options.groupByCategory
  store.markPromptDirty()
}
</script>

<template>
  <div class="generate-pane">
    <div class="generate-top-grid">
      <MaterialSelectionCard
        :filters="store.materialFilters"
        :summary="store.materialSummary"
        :items="store.materialItems"
        :loading="store.materialLoading"
        :has-more="store.materialHasMore"
        @update:filters="updateMaterialFilters"
        @toggle="store.toggleMaterial"
        @detail="store.openMaterialDetail"
        @load-more="store.loadMaterials(false)"
      />

      <PromptConfigCard
        :templates="store.templates"
        :selected-template-name="store.selectedTemplateName"
        :extra-requirements="store.extraRequirements"
        :output-focus="store.outputFocus"
        :options="store.promptOptions"
        :prompt-dirty="store.promptDirty"
        :prompt-loading="store.promptLoading"
        :selected-material-count="store.selectedMaterialCount"
        :estimated-prompt-chars="store.materialSummary.estimated_prompt_chars"
        @update:selected-template-name="store.selectedTemplateName = $event; store.markPromptDirty()"
        @update:extra-requirements="store.extraRequirements = $event; store.markPromptDirty()"
        @update:output-focus="store.outputFocus = $event; store.markPromptDirty()"
        @update:options="updatePromptOptions"
        @open-templates="store.templateDrawerVisible = true"
        @preview-prompt="buildPrompt"
      />
    </div>

    <ReportResultPreviewCard
      :markdown="store.generatedMarkdown"
      :prompt-text="store.promptText"
      :loading="store.generationLoading"
      :can-generate="store.canGenerate"
      :saved="store.generationSaved"
      :selected-date="store.selectedDate"
      :template-name="store.selectedTemplateName"
      @regenerate="generateReport"
      @copy="copyText"
      @save="store.saveCurrentReport"
    />
  </div>
</template>

<style scoped>
.generate-pane {
  min-width: 0;
  display: grid;
  gap: 14px;
  align-items: start;
}

.generate-top-grid {
  min-width: 0;
  height: min(680px, calc(100vh - 188px));
  min-height: 540px;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(480px, 0.95fr);
  gap: 14px;
  align-items: stretch;
}

:deep(.workbench-card) {
  min-width: 0;
  padding: 16px;
  border: 1px solid #dfe8f5;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 31, 61, 0.04);
}

@media (max-width: 1120px) {
  .generate-top-grid {
    height: auto;
    min-height: 0;
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
