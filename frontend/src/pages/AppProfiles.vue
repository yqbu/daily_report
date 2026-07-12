<script setup lang="ts">
import { computed, onMounted, shallowRef, useTemplateRef } from 'vue'
import { ElDrawer, ElMessage } from 'element-plus'
import { Check, Close, Download, Refresh } from '@element-plus/icons-vue'

import { callTypedDesktopApi } from '../api/desktop'
import type {
  AppCategoryConfig,
  AppProfileListFilters,
  AppProfileListPayload,
  SaveAppProfilePayload
} from '../api/types'
import { useAppProfileCache } from '../composables/useAppProfileCache'
import AppCategoryPanel from '../components/app-profiles/AppCategoryPanel.vue'
import AppProfileListPanel from '../components/app-profiles/AppProfileListPanel.vue'
import AppProfileOverview from '../components/app-profiles/AppProfileOverview.vue'
import {
  countProfiles,
  emptyAppProfileList,
  filterProfiles,
  normalizeClassification,
  paginateProfiles,
  sortProfiles
} from '../utils/appProfiles'

type FilterPatch = Partial<AppProfileListFilters>
type AppProfileListPanelInstance = InstanceType<typeof AppProfileListPanel>

const profileListPanel = useTemplateRef<AppProfileListPanelInstance>('profileListPanel')
const { readAppProfileCache, writeAppProfileCache, clearAppProfileCache } = useAppProfileCache()
const appProfileFilters = shallowRef<AppProfileListFilters>({
  classification: 'all',
  keyword: '',
  category: '',
  track_enabled: null,
  sort_by: 'last_seen',
  sort_direction: 'desc'
})
const appProfilePage = shallowRef(1)
const appProfilePageSize = shallowRef(500)
const appProfiles = shallowRef<AppProfileListPayload>(emptyAppProfileList())
const appCategories = shallowRef<AppCategoryConfig[]>([])
const appProfileLoading = shallowRef(true)
const appProfileError = shallowRef('')
const operationMessage = shallowRef('')
const savingAppKey = shallowRef('')
const categorySaving = shallowRef(false)
const appProfileDirty = shallowRef(false)
const bulkSaving = shallowRef(false)
const extractingAppProfiles = shallowRef(false)
const extractedPreviewActive = shallowRef(false)
const categoryDrawerVisible = shallowRef(false)
let appProfileLoadRequestId = 0

const appProfileRows = computed(() => {
  return paginateProfiles(
    sortProfiles(filterProfiles(appProfiles.value.items, normalizedFilters.value), normalizedFilters.value),
    appProfilePage.value,
    appProfilePageSize.value
  )
})
const appProfileSummary = computed(() => {
  return countProfiles(filterProfiles(appProfiles.value.items, normalizedCountFilters.value))
})
const selectedCategory = computed(() => appProfileFilters.value.category || '')
const saveStatus = computed(() => {
  if (extractingAppProfiles.value) {
    return {
      text: '提取中',
      tone: 'saving' as const
    }
  }

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
  const requestId = appProfileLoadRequestId + 1
  appProfileLoadRequestId = requestId
  appProfileLoading.value = true
  appProfileError.value = ''
  try {
    const profilesPayload = await callTypedDesktopApi('listAppProfiles', {
      filters: normalizedCatalogFilters.value,
      page: 1,
      pageSize: appProfilePageSize.value,
      include_unobserved: true,
      mode: 'saved',
      extract_if_empty: true,
      observed_scope: 'all'
    })
    if (requestId !== appProfileLoadRequestId) return
    appProfiles.value = profilesPayload
    appCategories.value = profilesPayload.categories
    extractedPreviewActive.value = profilesPayload.items.some((profile) => profile.requires_save && !profile.is_configured)
    writeAppProfileCache(profilesPayload)
  } catch (error) {
    if (requestId !== appProfileLoadRequestId) return
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    if (requestId === appProfileLoadRequestId) {
      appProfileLoading.value = false
    }
  }
}

async function extractAppProfilesFromForeground(): Promise<void> {
  const requestId = appProfileLoadRequestId + 1
  appProfileLoadRequestId = requestId
  extractingAppProfiles.value = true
  appProfileLoading.value = true
  appProfileError.value = ''
  try {
    const profilesPayload = await callTypedDesktopApi('extractAppProfiles', {
      filters: normalizedCatalogFilters.value,
      page: 1,
      pageSize: appProfilePageSize.value,
      include_unobserved: true,
      observed_scope: 'all'
    })
    if (requestId !== appProfileLoadRequestId) return
    appProfiles.value = profilesPayload
    appCategories.value = profilesPayload.categories
    extractedPreviewActive.value = true
    clearAppProfileCache()
    if (profilesPayload.items.length === 0) {
      flashOperationMessage('未提取到前台应用数据')
    } else {
      ElMessage.success(`已提取 ${profilesPayload.items.length} 个应用，点击保存后持久化`)
    }
  } catch (error) {
    if (requestId !== appProfileLoadRequestId) return
    showAppProfileError(error)
  } finally {
    if (requestId === appProfileLoadRequestId) {
      appProfileLoading.value = false
      extractingAppProfiles.value = false
    }
  }
}

const normalizedFilters = computed<AppProfileListFilters>(() => {
  const filters = appProfileFilters.value
  return {
    classification: filters.classification ?? 'all',
    keyword: filters.keyword?.trim() ?? '',
    category: filters.category?.trim() || undefined,
    track_enabled: filters.track_enabled ?? null,
    sort_by: filters.sort_by ?? 'last_seen',
    sort_direction: filters.sort_direction ?? 'desc'
  }
})

const normalizedCountFilters = computed<AppProfileListFilters>(() => {
  return {
    ...normalizedFilters.value,
    classification: 'all',
    track_enabled: null
  }
})

const normalizedCatalogFilters = computed<AppProfileListFilters>(() => {
  return {
    classification: 'all',
    keyword: '',
    category: undefined,
    track_enabled: null,
    sort_by: normalizedFilters.value.sort_by,
    sort_direction: normalizedFilters.value.sort_direction
  }
})

function updateFilters(patch: FilterPatch): void {
  appProfileFilters.value = {
    ...appProfileFilters.value,
    ...patch,
    classification: normalizeClassification(patch.classification ?? appProfileFilters.value.classification)
  }
  appProfilePage.value = 1
}

function clearCategoryFilter(): void {
  updateFilters({ category: '' })
}

function hydrateAppProfileCache(): boolean {
  const cached = readAppProfileCache()
  if (!cached) return false

  appProfiles.value = cached.payload
  appCategories.value = cached.payload.categories
  extractedPreviewActive.value = cached.payload.items.some((profile) => profile.requires_save && !profile.is_configured)
  return cached.fresh
}

async function saveAppProfileDraft(payload: SaveAppProfilePayload): Promise<void> {
  savingAppKey.value = payload.app_key
  appProfileError.value = ''
  try {
    await callTypedDesktopApi('saveAppProfile', payload)
    operationMessage.value = ''
    ElMessage.success('应用配置已保存')
    await loadAppProfileBootstrap()
  } catch (error) {
    showAppProfileError(error)
  } finally {
    savingAppKey.value = ''
  }
}

async function resetAppProfileDraft(appKey: string): Promise<void> {
  savingAppKey.value = appKey
  appProfileError.value = ''
  try {
    await callTypedDesktopApi('resetAppProfile', { app_key: appKey })
    operationMessage.value = ''
    ElMessage.success('已恢复默认配置')
    await loadAppProfileBootstrap()
  } catch (error) {
    showAppProfileError(error)
  } finally {
    savingAppKey.value = ''
  }
}

async function deleteAppProfileRecords(appKey: string): Promise<void> {
  savingAppKey.value = appKey
  appProfileError.value = ''
  try {
    const result = await callTypedDesktopApi('deleteAppRecords', { app_key: appKey })
    operationMessage.value = ''
    ElMessage.success(`已移除 ${result.deleted_count} 条历史记录`)
    await loadAppProfileBootstrap()
  } catch (error) {
    showAppProfileError(error)
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
      await callTypedDesktopApi('saveAppProfile', payload)
    }
    operationMessage.value = ''
    ElMessage.success(`已保存 ${payloads.length} 项应用配置`)
    await loadAppProfileBootstrap()
  } catch (error) {
    showAppProfileError(error)
  } finally {
    savingAppKey.value = ''
    bulkSaving.value = false
  }
}

function cancelAllAppProfileDrafts(): void {
  if (extractedPreviewActive.value) {
    extractedPreviewActive.value = false
    profileListPanel.value?.resetAllDrafts()
    void loadAppProfileBootstrap()
    flashOperationMessage('已取消提取预览')
    return
  }

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
    await callTypedDesktopApi('saveAppCategory', payload)
    operationMessage.value = ''
    ElMessage.success('分类已保存')
    await loadAppProfileBootstrap()
  } catch (error) {
    showAppProfileError(error)
  } finally {
    categorySaving.value = false
  }
}

async function deleteAppCategoryDraft(name: string): Promise<void> {
  categorySaving.value = true
  appProfileError.value = ''
  try {
    await callTypedDesktopApi('deleteAppCategory', { name, fallback_category: '其他' })
    if (selectedCategory.value === name) {
      appProfileFilters.value = { ...appProfileFilters.value, category: '' }
    }
    operationMessage.value = ''
    ElMessage.success('分类已删除')
    await loadAppProfileBootstrap()
  } catch (error) {
    showAppProfileError(error)
  } finally {
    categorySaving.value = false
  }
}

function showAppProfileError(error: unknown): void {
  const message = error instanceof Error ? error.message : String(error)
  appProfileError.value = message
  ElMessage.error(message)
}

function flashOperationMessage(message: string): void {
  operationMessage.value = message
  window.setTimeout(() => {
    if (operationMessage.value === message) {
      operationMessage.value = ''
    }
  }, 2600)
}

defineExpose({
  loadAppProfileBootstrap,
  saveAppProfileDraft,
  resetAppProfileDraft,
  deleteAppProfileRecords,
  saveAppCategoryDraft,
  deleteAppCategoryDraft
})

onMounted(() => {
  const cacheFresh = hydrateAppProfileCache()
  if (!cacheFresh) {
    void loadAppProfileBootstrap()
    return
  }

  appProfileLoading.value = false
})
const saveStatusClass = computed(() => `save-status--${saveStatus.value.tone}`)
</script>

<template>
  <div class="app-profiles-root">
    <header class="app-profiles-topbar">
      <div class="title-block">
        <span class="workspace-label">Daily Report</span>
        <h1 class="page-title">应用配置</h1>
      </div>

      <div class="top-actions">
        <button
          class="top-button"
          type="button"
          :disabled="appProfileLoading || bulkSaving || extractingAppProfiles"
          title="从前台应用数据提取用过的应用"
          @click="extractAppProfilesFromForeground"
        >
          <Download class="action-icon" />
          <span>提取应用</span>
        </button>
        <button
          class="top-button"
          type="button"
          :disabled="appProfileLoading || bulkSaving || extractingAppProfiles"
          title="刷新应用配置"
          @click="loadAppProfileBootstrap"
        >
          <Refresh class="action-icon" :class="{ 'action-icon--spin': appProfileLoading }" />
          <span>刷新</span>
        </button>
        <span class="save-status" :class="saveStatusClass">{{ saveStatus.text }}</span>
        <span class="top-action-divider" aria-hidden="true"></span>
        <button
          class="top-button"
          type="button"
          :disabled="!appProfileDirty || bulkSaving || extractingAppProfiles"
          @click="cancelAllAppProfileDrafts"
        >
          <Close class="action-icon" />
          <span>取消</span>
        </button>
        <button
          class="top-button top-button--primary"
          type="button"
          :disabled="!appProfileDirty || bulkSaving || extractingAppProfiles"
          @click="saveAllAppProfileDrafts"
        >
          <Check class="action-icon" />
          <span>保存</span>
        </button>
      </div>
    </header>

    <div class="app-profiles-page">
      <section class="app-profiles-pinned" aria-label="应用配置筛选与分类">
        <AppProfileOverview
          :counts="appProfileSummary"
          :filters="appProfileFilters"
          :loading="appProfileLoading"
          :message="operationMessage"
          :error="appProfileError"
          @refresh="loadAppProfileBootstrap"
          @manage-categories="categoryDrawerVisible = true"
          @update-filters="updateFilters"
        />
      </section>

      <AppProfileListPanel
        ref="profileListPanel"
        class="app-profiles-scroll-region"
        :profiles="appProfileRows"
        :categories="appCategories"
        :loading="appProfileLoading"
        :saving-app-key="savingAppKey"
        :error="appProfileError"
        @save="saveAppProfileDraft"
        @reset="resetAppProfileDraft"
        @delete-records="deleteAppProfileRecords"
        @dirty-change="updateAppProfileDirtyState"
      />
    </div>

    <el-drawer
      v-model="categoryDrawerVisible"
      title="应用分类管理"
      direction="rtl"
      size="420px"
      class="category-drawer"
    >
      <AppCategoryPanel
        class="drawer-category-panel"
        :categories="appCategories"
        :selected-category="selectedCategory"
        :loading="appProfileLoading"
        :saving="categorySaving"
        @create="saveAppCategoryDraft"
        @delete="deleteAppCategoryDraft"
        @select="updateFilters({ category: $event })"
        @clear="clearCategoryFilter"
      />
    </el-drawer>
  </div>
</template>

<style scoped>
.app-profiles-root {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  overflow: hidden;
}

.app-profiles-topbar {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
}

.title-block {
  min-width: 0;
}

.workspace-label {
  display: block;
  color: #667085;
  font-size: 12px;
  line-height: 1.2;
}

.page-title {
  margin: 4px 0 0;
  color: #172033;
  font-size: 22px;
  font-weight: 720;
  line-height: 1.15;
  letter-spacing: 0;
}

.top-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.save-status,
.top-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #526179;
  background: #ffffff;
  font-size: 13px;
  white-space: nowrap;
}

.save-status {
  background: #f8fafc;
}

.save-status--dirty {
  color: #92400e;
  background: #fffbeb;
  border-color: #fde68a;
}

.save-status--saving {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.save-status--saved {
  color: #047857;
  background: #ecfdf5;
  border-color: #bbf7d0;
}

.save-status--error {
  color: #b42318;
  background: #fef2f2;
  border-color: #fecaca;
}

.top-action-divider {
  width: 1px;
  height: 24px;
  flex: 0 0 auto;
  background: #dce3ee;
}

.top-button {
  cursor: pointer;
}

.top-button:hover {
  color: #2563eb;
  border-color: #c9dcff;
  background: #eff6ff;
}

.top-button--primary {
  color: #ffffff;
  border-color: #2563eb;
  background: #2563eb;
}

.top-button--primary:hover {
  color: #ffffff;
  border-color: #1d4ed8;
  background: #1d4ed8;
}

.top-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.action-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.action-icon--spin {
  animation: app-profiles-spin 900ms linear infinite;
}

.app-profiles-page {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
  overflow: hidden;
}

.app-profiles-pinned {
  min-height: 0;
}

.app-profiles-scroll-region {
  min-height: 0;
}

.drawer-category-panel {
  height: 100%;
  border: 0;
  border-radius: 0;
}

:deep(.category-drawer .el-drawer__body) {
  min-height: 0;
  padding: 0;
  overflow: hidden;
}

@keyframes app-profiles-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .app-profiles-topbar {
    min-height: auto;
    align-items: flex-start;
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 2px;
  }
}

</style>
