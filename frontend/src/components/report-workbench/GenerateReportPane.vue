<script setup lang="ts">
import GenerateStepSidebar from './GenerateStepSidebar.vue'
import MaterialSelectionCard from './MaterialSelectionCard.vue'
import PromptConfigCard from './PromptConfigCard.vue'
import ReportResultPreviewCard from './ReportResultPreviewCard.vue'
import SubmitSummaryCard from './SubmitSummaryCard.vue'
import FinalPromptPreviewCard from './FinalPromptPreviewCard.vue'
import { useReportWorkbenchStore } from '../../stores/reportWorkbench'
import type { GenerateStep, MaterialFilters, PromptOptions } from '../../types/reportWorkbench'

defineProps<{
  selectedDate: string
  activeStep: GenerateStep
  completedSteps: number[]
  disabledSteps: number[]
  modelLabel?: string
}>()

const emit = defineEmits<{
  'update:selectedDate': [value: string]
  'update:activeStep': [value: GenerateStep]
  buildPrompt: []
  generate: []
}>()

const store = useReportWorkbenchStore()

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

function updateSelectedTemplateName(value: string): void {
  store.selectedTemplateName = value
  store.markPromptDirty()
}

function updateExtraRequirements(value: string): void {
  store.extraRequirements = value
  store.markPromptDirty()
}

function updateOutputFocus(value: string[]): void {
  store.outputFocus = value
  store.markPromptDirty()
}
</script>

<template>
  <div class="generate-pane">
    <div class="generate-step-layout">
      <GenerateStepSidebar
        :selected-date="selectedDate"
        :active-step="activeStep"
        :completed-steps="completedSteps"
        :disabled-steps="disabledSteps"
        @update:selected-date="emit('update:selectedDate', $event)"
        @change="emit('update:activeStep', $event)"
      />

      <main class="generate-step-content">
        <section v-if="activeStep === 0" class="step-pane">
          <MaterialSelectionCard
            :filters="store.materialFilters"
            :summary="store.materialSummary"
            :items="store.materialItems"
            :loading="store.materialLoading"
            :has-more="store.materialHasMore"
            :show-header="false"
            @update:filters="updateMaterialFilters"
            @toggle="store.toggleMaterial"
            @detail="store.openMaterialDetail"
            @load-more="store.loadMaterials(false)"
          />
        </section>

        <section v-else-if="activeStep === 1" class="step-pane">
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
            :model-label="modelLabel"
            :show-header="false"
            :show-actions="false"
            @update:selected-template-name="updateSelectedTemplateName"
            @update:extra-requirements="updateExtraRequirements"
            @update:output-focus="updateOutputFocus"
            @update:options="updatePromptOptions"
            @open-templates="store.templateDrawerVisible = true"
          />
        </section>

        <section v-else-if="activeStep === 2" class="step-pane step-pane--confirm">
          <SubmitSummaryCard
            :summary="store.materialSummary"
            :selected-materials="store.selectedMaterials"
            :selected-template="store.selectedTemplate"
            :output-focus="store.outputFocus"
            :extra-requirements="store.extraRequirements"
            :prompt-dirty="store.promptDirty"
            :prompt-text="store.promptText"
            :generating="store.generationLoading"
            :can-generate="store.canGenerate"
            :show-actions="false"
            @edit-materials="emit('update:activeStep', 0)"
            @edit-prompt="emit('update:activeStep', 1)"
            @build-prompt="emit('buildPrompt')"
            @generate="emit('generate')"
          />

          <FinalPromptPreviewCard
            :prompt-text="store.promptText"
            :prompt-dirty="store.promptDirty"
            :selected-materials="store.selectedMaterials"
            :selected-template="store.selectedTemplate"
            :extra-requirements="store.extraRequirements"
            :output-focus="store.outputFocus"
            :options="store.promptOptions"
          />
        </section>

        <section v-else class="step-pane step-pane--result">
          <ReportResultPreviewCard
            :markdown="store.generatedMarkdown"
            :prompt-text="store.promptText"
            :loading="store.generationLoading"
            :can-generate="store.canGenerate"
            :saved="store.generationSaved"
            :selected-date="store.selectedDate"
            :template-name="store.selectedTemplateName"
            :show-header="false"
            :show-actions="false"
          />
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.generate-pane {
  container-type: inline-size;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.generate-step-layout {
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-columns: 204px minmax(0, 1fr);
  gap: 14px;
  overflow: hidden;
}

.generate-step-content {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.step-pane {
  height: 100%;
  min-width: 0;
  min-height: 0;
}

.step-pane--confirm {
  display: grid;
  grid-template-columns: minmax(280px, 0.58fr) minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
}

.step-pane--result {
  display: grid;
  min-height: 0;
}

:deep(.workbench-card) {
  min-width: 0;
  padding: 16px;
  border: 1px solid #dfe8f5;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 31, 61, 0.04);
}

@media (max-width: 860px) {
  .generate-step-layout {
    height: auto;
    min-height: 0;
    grid-template-columns: minmax(0, 1fr);
    overflow: visible;
  }

  .generate-pane,
  .generate-step-content {
    overflow: visible;
  }

  .step-pane,
  .step-pane--confirm {
    height: auto;
  }

  .step-pane--confirm {
    grid-template-columns: minmax(0, 1fr);
  }
}

@container (max-width: 860px) {
  .generate-step-layout {
    height: auto;
    min-height: 0;
    grid-template-columns: minmax(0, 1fr);
    overflow: visible;
  }

  .generate-pane,
  .generate-step-content {
    overflow: visible;
  }

  .step-pane,
  .step-pane--confirm {
    height: auto;
  }

  .step-pane--confirm {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
