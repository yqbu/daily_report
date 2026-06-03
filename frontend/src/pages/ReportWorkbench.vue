<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Check,
  CopyDocument,
  Delete,
  Download,
  MagicStick,
  Refresh,
  Select,
  Tickets,
  View
} from '@element-plus/icons-vue'

import MaterialOrganizedPreview from '../components/report-workbench/MaterialOrganizedPreview.vue'
import PromptOrganizedPreview from '../components/report-workbench/PromptOrganizedPreview.vue'
import PromptPreviewDrawer from '../components/report-workbench/PromptPreviewDrawer.vue'
import RecordDetailDrawer from '../components/data-center/RecordDetailDrawer.vue'
import ReportWorkbenchTabs from '../components/report-workbench/ReportWorkbenchTabs.vue'
import ReportWorkbenchTopbar from '../components/report-workbench/ReportWorkbenchTopbar.vue'
import TemplateManagerDrawer from '../components/report-workbench/TemplateManagerDrawer.vue'
import { useReportWorkbenchStore } from '../stores/reportWorkbench'
import { useSettingsStore } from '../stores/settings'
import type { LocalSettingsPayload } from '../api/types'
import type { DetailSavePayload, GenerateStep, ReportTopbarAction } from '../types/reportWorkbench'

const store = useReportWorkbenchStore()
const settingsStore = useSettingsStore()
const route = useRoute()
const router = useRouter()
const activeGenerateStep = shallowRef<GenerateStep>(0)
const materialPreviewVisible = shallowRef(false)
const promptOrganizedPreviewVisible = shallowRef(false)

const hasSelectedMaterials = computed(() => store.selectedMaterialCount > 0 || store.materialSummary.total_count === 0)
const completedGenerateSteps = computed(() => {
  const steps: number[] = []
  if (hasSelectedMaterials.value) steps.push(0)
  if (store.promptText && !store.promptDirty) steps.push(1)
  if (store.promptText && !store.promptDirty && hasSelectedMaterials.value) steps.push(2)
  if (store.generatedMarkdown) steps.push(3)
  return steps
})
const disabledGenerateSteps = computed(() => (store.generatedMarkdown ? [] : [3]))
const selectedMaterialItems = computed(() => store.materialItems.filter((item) => item.is_selected))
const modelLabel = computed(() => {
  const settings = settingsStore.settings as LocalSettingsPayload | null
  const modelName = settings?.model?.model_name?.trim()
  const provider = settings?.model?.provider?.trim()
  if (modelName && provider) return `${provider} / ${modelName}`
  return modelName || 'deepseek-chat'
})

const topbarActions = computed<ReportTopbarAction[]>(() => {
  if (store.activeTab !== 'generate') {
    return []
  }

  if (activeGenerateStep.value === 0) {
    return [
      {
        id: 'clear-materials',
        label: '清空选择',
        icon: Delete,
        disabled: selectedMaterialItems.value.length === 0
      },
      {
        id: 'select-non-sensitive',
        label: '仅选择非敏感',
        icon: Select,
        disabled: store.materialItems.length === 0 || store.materialLoading,
        loading: store.materialLoading
      },
      {
        id: 'preview-materials',
        label: '预览素材',
        icon: View
      },
      {
        id: 'configure-prompt',
        label: '配置 Prompt',
        icon: MagicStick,
        tone: 'primary',
        disabled: !hasSelectedMaterials.value
      }
    ]
  }

  if (activeGenerateStep.value === 1) {
    return [
      {
        id: 'open-templates',
        label: '模板管理',
        icon: Tickets
      },
      {
        id: 'preview-prompt',
        label: '预览 Prompt',
        icon: View
      },
      {
        id: 'build-prompt',
        label: '构建 Prompt',
        icon: MagicStick,
        tone: 'primary',
        loading: store.promptLoading,
        disabled: !hasSelectedMaterials.value
      }
    ]
  }

  if (activeGenerateStep.value === 2) {
    return [
      {
        id: 'generate-report',
        label: '生成日报',
        icon: Select,
        tone: 'primary',
        loading: store.generationLoading,
        disabled: !store.canGenerate
      }
    ]
  }

  return [
    {
      id: 'regenerate-report',
      label: '重新生成',
      icon: Refresh,
      loading: store.generationLoading,
      disabled: !store.canGenerate
    },
    {
      id: 'copy-markdown',
      label: '复制 Markdown',
      icon: CopyDocument,
      disabled: !store.generatedMarkdown
    },
    {
      id: 'export-markdown',
      label: '导出 .md',
      icon: Download,
      disabled: !store.generatedMarkdown
    },
    {
      id: 'save-report',
      label: store.generationSaved ? '已保存' : '保存',
      icon: Check,
      tone: 'success',
      disabled: !store.generatedMarkdown || store.generationSaved
    }
  ]
})

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

async function changeDate(date: string): Promise<void> {
  await store.changeDate(date)
  activeGenerateStep.value = 0
}

function changeGenerateStep(step: GenerateStep): void {
  if (step > 0 && step < 3 && !hasSelectedMaterials.value) {
    activeGenerateStep.value = 0
    ElMessage.warning('请先选择至少一条素材')
    return
  }
  if (step === 3 && !store.generatedMarkdown) {
    ElMessage.warning('请先在内容确认步骤中生成日报')
    return
  }
  activeGenerateStep.value = step
}

async function buildPrompt(goConfirm = false): Promise<void> {
  if (!hasSelectedMaterials.value) {
    activeGenerateStep.value = 0
    ElMessage.warning('请先选择至少一条素材')
    return
  }
  try {
    await store.buildCurrentPrompt(false)
    if (goConfirm) {
      promptOrganizedPreviewVisible.value = false
      activeGenerateStep.value = 2
    }
    ElMessage.success('Prompt 已构建')
  } catch {
    ElMessage.error('Prompt 构建失败，请检查模型配置或网络连接')
  }
}

async function generateReport(): Promise<void> {
  if (!hasSelectedMaterials.value) {
    activeGenerateStep.value = 0
    ElMessage.warning('请先选择至少一条素材')
    return
  }
  try {
    await store.generateCurrentReport()
    activeGenerateStep.value = 3
    ElMessage.success('日报已生成')
  } catch {
    ElMessage.error('日报生成失败，请检查模型配置或网络连接。')
  }
}

async function clearMaterialSelection(): Promise<void> {
  if (!selectedMaterialItems.value.length) {
    ElMessage.info('当前列表没有已选素材')
    return
  }
  await store.batchSelect(selectedMaterialItems.value, false)
  ElMessage.success('已清空当前列表中的素材选择')
}

async function selectNonSensitiveMaterials(): Promise<void> {
  const items = store.materialItems.filter((item) => !item.is_sensitive)
  if (!items.length) {
    ElMessage.info('当前列表没有可选择的非敏感素材')
    return
  }
  await store.batchSelect(items, true)
  ElMessage.success('已选择当前列表中的非敏感素材')
}

function exportMarkdown(): void {
  if (!store.generatedMarkdown) {
    return
  }
  const blob = new Blob([store.generatedMarkdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `daily-report-${store.selectedDate}.md`
  link.click()
  URL.revokeObjectURL(url)
}

async function saveCurrentReport(): Promise<void> {
  await store.saveCurrentReport()
  ElMessage.success('日报已保存')
}

async function handleTopbarAction(id: string): Promise<void> {
  switch (id) {
    case 'clear-materials':
      await clearMaterialSelection()
      break
    case 'select-non-sensitive':
      await selectNonSensitiveMaterials()
      break
    case 'preview-materials':
      materialPreviewVisible.value = true
      break
    case 'configure-prompt':
      changeGenerateStep(1)
      break
    case 'open-templates':
      store.templateDrawerVisible = true
      break
    case 'preview-prompt':
      promptOrganizedPreviewVisible.value = true
      break
    case 'build-prompt':
      await buildPrompt(true)
      break
    case 'generate-report':
    case 'regenerate-report':
      await generateReport()
      break
    case 'copy-markdown':
      await copyText(store.generatedMarkdown)
      break
    case 'export-markdown':
      exportMarkdown()
      break
    case 'save-report':
      await saveCurrentReport()
      break
  }
}

watch(
  () => store.activeTab,
  (tab) => {
    if (tab === 'history') {
      void store.loadHistory()
    }
    const currentTab = normalizeReportTab(route.query.tab)
    if (tab !== currentTab) {
      void router.replace({ query: { ...route.query, tab } })
    }
  }
)

watch(
  () => route.query.tab,
  (tab) => {
    const normalized = normalizeReportTab(tab)
    if (store.activeTab !== normalized) {
      store.activeTab = normalized
    }
  },
  { immediate: true }
)

function normalizeReportTab(value: unknown): 'generate' | 'history' {
  return value === 'history' ? 'history' : 'generate'
}

onMounted(async () => {
  await Promise.all([store.refreshMaterials(), store.loadHistory(), settingsStore.loadSettings()])
})
</script>

<template>
  <div class="report-workbench-page">
    <ReportWorkbenchTopbar
      :actions="topbarActions"
      @action="handleTopbarAction"
    />

    <ReportWorkbenchTabs
      class="report-workbench-content"
      :active-tab="store.activeTab"
      :selected-date="store.selectedDate"
      :generate-step="activeGenerateStep"
      :completed-steps="completedGenerateSteps"
      :disabled-steps="disabledGenerateSteps"
      :model-label="modelLabel"
      @update:selected-date="changeDate"
      @update:generate-step="changeGenerateStep"
      @build-prompt="buildPrompt(false)"
      @generate="generateReport"
    />

    <el-drawer
      v-model="materialPreviewVisible"
      class="report-preview-drawer"
      title="素材组织预览"
      size="520px"
      append-to-body
    >
      <MaterialOrganizedPreview
        :items="store.materialItems"
        :summary="store.materialSummary"
        :loading="store.materialLoading"
        :show-actions="false"
        @next="materialPreviewVisible = false; changeGenerateStep(1)"
        @clear-selection="clearMaterialSelection"
        @select-non-sensitive="selectNonSensitiveMaterials"
      />
    </el-drawer>

    <el-drawer
      v-model="promptOrganizedPreviewVisible"
      class="report-preview-drawer"
      title="Prompt 组织预览"
      size="560px"
      append-to-body
    >
      <PromptOrganizedPreview
        :template="store.selectedTemplate"
        :extra-requirements="store.extraRequirements"
        :output-focus="store.outputFocus"
        :options="store.promptOptions"
        :selected-material-count="store.selectedMaterialCount"
        :estimated-prompt-chars="store.materialSummary.estimated_prompt_chars"
        :prompt-dirty="store.promptDirty"
        :show-actions="false"
        @previous="promptOrganizedPreviewVisible = false; changeGenerateStep(0)"
        @next="promptOrganizedPreviewVisible = false; changeGenerateStep(2)"
        @build-prompt="buildPrompt(false)"
      />
    </el-drawer>

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
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  overflow: hidden;
  color: #172033;
  background: #fbfcfd;
}

.report-workbench-content {
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

:global(.report-preview-drawer .el-drawer__body) {
  min-height: 0;
  display: grid;
  padding: 16px;
  overflow: hidden;
}

:global(.report-preview-drawer .workbench-card) {
  height: 100%;
  border: 1px solid #dfe8f5;
  box-shadow: none;
}
</style>
