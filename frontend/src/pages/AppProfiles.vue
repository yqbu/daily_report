<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

import { callTypedBridge } from '../api/bridge'
import type {
  AppCategoryConfig,
  AppProfileClassificationFilter,
  AppProfileConfig,
  AppProfileListFilters,
  AppProfileListPayload,
  SaveAppProfilePayload
} from '../api/types'
import AppCategoryPanel from '../components/app-profiles/AppCategoryPanel.vue'
import AppProfileListPanel from '../components/app-profiles/AppProfileListPanel.vue'
import AppProfileOverview from '../components/app-profiles/AppProfileOverview.vue'
import PageLayout from '../layouts/PageLayout.vue'
import { useAppStore } from '../stores/app'

type FilterPatch = Partial<AppProfileListFilters>
type AppProfileListPanelInstance = InstanceType<typeof AppProfileListPanel>

const appStore = useAppStore()
const profileListPanel = useTemplateRef<AppProfileListPanelInstance>('profileListPanel')
const appProfileFilters = shallowRef<AppProfileListFilters>({
  classification: 'all',
  keyword: '',
  category: '',
  track_enabled: null
})
const appProfilePage = shallowRef(1)
const appProfilePageSize = shallowRef(200)
const appProfiles = shallowRef<AppProfileListPayload>(emptyAppProfileList())
const appCategories = shallowRef<AppCategoryConfig[]>([])
const appProfileLoading = shallowRef(false)
const appProfileError = shallowRef('')
const operationMessage = shallowRef('')
const savingAppKey = shallowRef('')
const categorySaving = shallowRef(false)
const appProfileDirty = shallowRef(false)
const bulkSaving = shallowRef(false)

const appProfileSummary = computed(() => appProfiles.value.counts)
const appProfileRows = computed(() => appProfiles.value.items)
const selectedCategory = computed(() => appProfileFilters.value.category || '')
const topBarSaveStatus = computed(() => {
  if (bulkSaving.value) {
    return {
      text: '保存中',
      tone: 'saving' as const
    }
  }

  if (appProfileError.value) {
    return {
      text: '保存失败',
      tone: 'error' as const
    }
  }

  if (appProfileDirty.value) {
    return {
      text: '有未保存更改',
      tone: 'dirty' as const
    }
  }

  return {
    text: operationMessage.value || '已保存',
    tone: 'saved' as const
  }
})

async function loadAppProfileBootstrap(): Promise<void> {
  appProfileLoading.value = true
  appProfileError.value = ''
  try {
    const [profilesPayload, categoriesPayload] = await Promise.all([
      callTypedBridge('listAppProfiles', {
        filters: normalizedFilters.value,
        page: appProfilePage.value,
        pageSize: appProfilePageSize.value,
        include_unobserved: true
      }),
      callTypedBridge('listAppCategories', { include_deleted: false })
    ])
    appProfiles.value = profilesPayload
    appCategories.value = categoriesPayload.items
  } catch (error) {
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    appProfileLoading.value = false
  }
}

const normalizedFilters = computed<AppProfileListFilters>(() => {
  const filters = appProfileFilters.value
  return {
    classification: filters.classification ?? 'all',
    keyword: filters.keyword?.trim() ?? '',
    category: filters.category?.trim() || undefined,
    track_enabled: filters.track_enabled ?? null
  }
})

async function updateFilters(patch: FilterPatch): Promise<void> {
  appProfileFilters.value = {
    ...appProfileFilters.value,
    ...patch,
    classification: normalizeClassification(patch.classification ?? appProfileFilters.value.classification)
  }
  appProfilePage.value = 1
  await loadAppProfileBootstrap()
}

async function clearCategoryFilter(): Promise<void> {
  await updateFilters({ category: '' })
}

async function saveAppProfileDraft(payload: SaveAppProfilePayload): Promise<void> {
  savingAppKey.value = payload.app_key
  appProfileError.value = ''
  try {
    await callTypedBridge('saveAppProfile', payload)
    flashOperationMessage('应用配置已保存')
    await loadAppProfileBootstrap()
  } catch (error) {
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    savingAppKey.value = ''
  }
}

async function resetAppProfileDraft(appKey: string): Promise<void> {
  savingAppKey.value = appKey
  appProfileError.value = ''
  try {
    await callTypedBridge('resetAppProfile', { app_key: appKey })
    flashOperationMessage('已恢复默认配置')
    await loadAppProfileBootstrap()
  } catch (error) {
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    savingAppKey.value = ''
  }
}

async function deleteAppProfileRecords(appKey: string): Promise<void> {
  savingAppKey.value = appKey
  appProfileError.value = ''
  try {
    const result = await callTypedBridge('deleteAppRecords', { app_key: appKey })
    flashOperationMessage(`已移除 ${result.deleted_count} 条历史记录`)
    await loadAppProfileBootstrap()
  } catch (error) {
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    savingAppKey.value = ''
  }
}

async function saveAllAppProfileDrafts(): Promise<void> {
  const payloads = profileListPanel.value?.getChangedPayloads() ?? []
  if (payloads.length === 0) {
    appProfileDirty.value = false
    return
  }

  bulkSaving.value = true
  appProfileError.value = ''
  try {
    for (const payload of payloads) {
      savingAppKey.value = payload.app_key
      await callTypedBridge('saveAppProfile', payload)
    }
    flashOperationMessage(`已保存 ${payloads.length} 项应用配置`)
    await loadAppProfileBootstrap()
  } catch (error) {
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    savingAppKey.value = ''
    bulkSaving.value = false
  }
}

function cancelAllAppProfileDrafts(): void {
  profileListPanel.value?.resetAllDrafts()
  flashOperationMessage('已取消未保存修改')
}

function updateAppProfileDirtyState(dirty: boolean): void {
  appProfileDirty.value = dirty
}

async function saveAppCategoryDraft(payload: { name: string; color: string }): Promise<void> {
  categorySaving.value = true
  appProfileError.value = ''
  try {
    await callTypedBridge('saveAppCategory', payload)
    flashOperationMessage('分类已保存')
    await loadAppProfileBootstrap()
  } catch (error) {
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    categorySaving.value = false
  }
}

async function deleteAppCategoryDraft(name: string): Promise<void> {
  categorySaving.value = true
  appProfileError.value = ''
  try {
    await callTypedBridge('deleteAppCategory', { name, fallback_category: '其他' })
    if (selectedCategory.value === name) {
      appProfileFilters.value = { ...appProfileFilters.value, category: '' }
    }
    flashOperationMessage('分类已删除')
    await loadAppProfileBootstrap()
  } catch (error) {
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    categorySaving.value = false
  }
}

function flashOperationMessage(message: string): void {
  operationMessage.value = message
  window.setTimeout(() => {
    if (operationMessage.value === message) {
      operationMessage.value = ''
    }
  }, 2600)
}

function normalizeClassification(
  value: AppProfileClassificationFilter | undefined
): AppProfileClassificationFilter {
  return value ?? 'all'
}

watch(
  topBarSaveStatus,
  (status) => {
    appStore.setTopBarState({
      mode: 'app-config',
      statusText: status.text,
      statusTone: status.tone,
      canCancel: appProfileDirty.value && !bulkSaving.value,
      canSave: appProfileDirty.value && !bulkSaving.value,
      saving: bulkSaving.value
    })
  },
  { immediate: true }
)

watch(
  () => appStore.topBar.saveRequestId,
  () => {
    if (appStore.topBar.mode !== 'app-config') return
    void saveAllAppProfileDrafts()
  }
)

watch(
  () => appStore.topBar.cancelRequestId,
  () => {
    if (appStore.topBar.mode !== 'app-config') return
    cancelAllAppProfileDrafts()
  }
)

defineExpose({
  loadAppProfileBootstrap,
  saveAppProfileDraft,
  resetAppProfileDraft,
  deleteAppProfileRecords,
  saveAppCategoryDraft,
  deleteAppCategoryDraft
})

onMounted(() => {
  void loadAppProfileBootstrap()
})

onBeforeUnmount(() => {
  appStore.resetTopBarState()
})

function emptyAppProfileList(): AppProfileListPayload {
  return {
    items: [],
    total: 0,
    page: 1,
    page_size: 200,
    counts: {
      all: 0,
      classified: 0,
      unclassified: 0,
      configured: 0,
      excluded: 0
    },
    categories: []
  }
}
</script>

<template>
  <PageLayout title="应用配置" subtitle="维护应用名称、分类颜色、采集开关和历史记录策略。">
    <div class="app-profiles-page">
      <section class="app-profiles-pinned" aria-label="应用配置筛选与分类">
        <AppProfileOverview
          :counts="appProfileSummary"
          :filters="appProfileFilters"
          :loading="appProfileLoading"
          :message="operationMessage"
          :error="appProfileError"
          @refresh="loadAppProfileBootstrap"
          @update-filters="updateFilters"
        />

        <AppCategoryPanel
          :categories="appCategories"
          :selected-category="selectedCategory"
          :loading="appProfileLoading"
          :saving="categorySaving"
          @create="saveAppCategoryDraft"
          @delete="deleteAppCategoryDraft"
          @select="updateFilters({ category: $event })"
          @clear="clearCategoryFilter"
        />
      </section>

      <AppProfileListPanel
        ref="profileListPanel"
        class="app-profiles-scroll-region"
        :profiles="appProfileRows"
        :categories="appCategories"
        :total="appProfiles.total"
        :loading="appProfileLoading"
        :saving-app-key="savingAppKey"
        :error="appProfileError"
        @save="saveAppProfileDraft"
        @reset="resetAppProfileDraft"
        @delete-records="deleteAppProfileRecords"
        @dirty-change="updateAppProfileDirtyState"
      >
        <template #actions>
          <button class="refresh-button" type="button" :disabled="appProfileLoading" @click="loadAppProfileBootstrap">
            <Refresh class="refresh-button-icon" />
            <span>刷新</span>
          </button>
        </template>
      </AppProfileListPanel>
    </div>
  </PageLayout>
</template>

<style scoped>
.app-profiles-page {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: 232px minmax(0, 1fr);
  gap: 16px;
}

.app-profiles-pinned {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.92fr);
  gap: 16px;
}

.app-profiles-scroll-region {
  min-height: 0;
}

.refresh-button {
  height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 12px;
  border: 1px solid #c9dcff;
  border-radius: 8px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 13px;
  font-weight: 720;
  line-height: 1;
  cursor: pointer;
}

.refresh-button:hover {
  border-color: #93c5fd;
  background: #dbeafe;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.62;
}

.refresh-button-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

@media (max-width: 980px) {
  .app-profiles-page {
    grid-template-rows: auto minmax(0, 1fr);
  }

  .app-profiles-pinned {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
