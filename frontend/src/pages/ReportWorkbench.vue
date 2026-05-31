<script setup lang="ts">
import { nextTick, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'

import ReportWorkbenchTabs from '../components/report-workbench/ReportWorkbenchTabs.vue'
import ReportWorkbenchTopbar from '../components/report-workbench/ReportWorkbenchTopbar.vue'
import TemplateManagerDrawer from '../components/report-workbench/TemplateManagerDrawer.vue'
import PromptPreviewDrawer from '../components/report-workbench/PromptPreviewDrawer.vue'
import RecordDetailDrawer from '../components/data-center/RecordDetailDrawer.vue'
import { useReportWorkbenchStore } from '../stores/reportWorkbench'
import type { DetailSavePayload } from '../types/reportWorkbench'

const store = useReportWorkbenchStore()

async function copyText(text: string): Promise<void> {
  if (!text) {
    return
  }
  await navigator.clipboard?.writeText(text)
  ElMessage.success('内容已复制')
}

async function saveDetail(payload: DetailSavePayload): Promise<void> {
  await store.saveMaterialDetail(payload)
  ElMessage.success('素材详情已更新')
}

async function generateFromTopbar(): Promise<void> {
  store.activeTab = 'generate'
  await nextTick()
  scrollResultIntoView()
  try {
    await store.generateCurrentReport()
    await nextTick()
    scrollResultIntoView()
    ElMessage.success('日报已生成')
  } catch {
    ElMessage.error('日报生成失败，请检查模型配置或网络连接。')
  }
}

function scrollResultIntoView(): void {
  const resultCard = document.querySelector('.result-card')
  resultCard?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

watch(
  () => store.activeTab,
  (tab) => {
    if (tab === 'history') {
      void store.loadHistory()
    }
  }
)

onMounted(async () => {
  await store.refreshMaterials()
  await store.loadHistory()
})
</script>

<template>
  <div class="report-workbench-page">
    <ReportWorkbenchTopbar
      :selected-date="store.selectedDate"
      :loading="store.materialLoading"
      :generating="store.generationLoading"
      :can-generate="store.canGenerate"
      @update:selected-date="store.changeDate"
      @refresh="store.refreshMaterials"
      @generate="generateFromTopbar"
    />

    <main class="report-workbench-body">
      <ReportWorkbenchTabs v-model:active-tab="store.activeTab" />
    </main>

    <TemplateManagerDrawer
      v-model="store.templateDrawerVisible"
      :templates="store.templates"
      @save="store.saveTemplate"
      @delete="store.deleteTemplate"
      @set-default="store.setDefaultTemplate"
    />

    <PromptPreviewDrawer
      v-model="store.promptPreviewVisible"
      :prompt-text="store.promptText"
      :template-name="store.selectedTemplate?.name || store.selectedTemplateName"
      :selected-material-count="store.selectedMaterialCount"
      :extra-requirements="store.extraRequirements"
      :warnings="store.promptWarnings"
      @copy="copyText"
    />

    <RecordDetailDrawer
      v-model="store.materialDetailDrawerVisible"
      :record="store.selectedMaterialDetail"
      :loading="store.materialDetailLoading"
      :saving="store.materialDetailSaving"
      @save="saveDetail"
      @delete="store.materialDetailDrawerVisible = false"
    />
  </div>
</template>

<style scoped>
.report-workbench-page {
  height: 100%;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  color: #172033;
  background: #fbfcfd;
}

.report-workbench-body {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #dfe8f5;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 24px rgba(15, 31, 61, 0.04);
}
</style>
