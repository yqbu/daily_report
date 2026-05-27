<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

import { callTypedBridge } from '../api/bridge'
import type {
  AppCategoryConfig,
  AppProfileClassificationFilter,
  AppProfileConfig,
  AppProfileCounts,
  AppProfileListFilters,
  AppProfileListPayload,
  SaveAppProfilePayload
} from '../api/types'
import AppCategoryPanel from '../components/app-profiles/AppCategoryPanel.vue'
import AppProfileListPanel from '../components/app-profiles/AppProfileListPanel.vue'
import AppProfileOverview from '../components/app-profiles/AppProfileOverview.vue'
import { useAppStore } from '../stores/app'

type FilterPatch = Partial<AppProfileListFilters>
type AppProfileListPanelInstance = InstanceType<typeof AppProfileListPanel>

const appProfileCollator = new Intl.Collator('zh-CN', {
  numeric: true,
  sensitivity: 'base'
})

const appStore = useAppStore()
const profileListPanel = useTemplateRef<AppProfileListPanelInstance>('profileListPanel')
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
const appProfileLoading = shallowRef(false)
const appProfileError = shallowRef('')
const operationMessage = shallowRef('')
const savingAppKey = shallowRef('')
const categorySaving = shallowRef(false)
const appProfileDirty = shallowRef(false)
const bulkSaving = shallowRef(false)
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
  const requestId = appProfileLoadRequestId + 1
  appProfileLoadRequestId = requestId
  appProfileLoading.value = true
  appProfileError.value = ''
  try {
    const profilesPayload = await callTypedBridge('listAppProfiles', {
      filters: normalizedCatalogFilters.value,
      page: 1,
      pageSize: appProfilePageSize.value,
      include_unobserved: true
    })
    if (requestId !== appProfileLoadRequestId) return
    appProfiles.value = profilesPayload
    appCategories.value = profilesPayload.categories
  } catch (error) {
    if (requestId !== appProfileLoadRequestId) return
    appProfileError.value = error instanceof Error ? error.message : String(error)
  } finally {
    if (requestId === appProfileLoadRequestId) {
      appProfileLoading.value = false
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
    classification: 'all'
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
  [topBarSaveStatus, appProfileDirty, bulkSaving, appProfileLoading],
  ([status]) => {
    appStore.setTopBarState({
      mode: 'app-config',
      statusText: status.text,
      statusTone: status.tone,
      canCancel: appProfileDirty.value && !bulkSaving.value,
      canRefresh: !bulkSaving.value,
      canSave: appProfileDirty.value && !bulkSaving.value,
      refreshing: appProfileLoading.value,
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

watch(
  () => appStore.topBar.refreshRequestId,
  () => {
    if (appStore.topBar.mode !== 'app-config') return
    void loadAppProfileBootstrap()
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
    page_size: 500,
    counts: emptyAppProfileCounts(),
    categories: []
  }
}

function emptyAppProfileCounts(): AppProfileCounts {
  return {
    all: 0,
    classified: 0,
    unclassified: 0,
    configured: 0,
    excluded: 0
  }
}

function filterProfiles(
  profiles: readonly AppProfileConfig[],
  filters: AppProfileListFilters
): AppProfileConfig[] {
  const keyword = filters.keyword?.trim().toLocaleLowerCase() ?? ''
  const category = filters.category?.trim() ?? ''
  const classification = filters.classification ?? 'all'
  const trackEnabled = filters.track_enabled ?? null

  return profiles.filter((profile) => {
    if (keyword && !profileMatchesKeyword(profile, keyword)) return false
    if (category && profile.category !== category) return false
    if (classification === 'classified' && !profile.is_classified) return false
    if (classification === 'unclassified' && profile.is_classified) return false
    if (classification === 'configured' && !profile.is_configured) return false
    if (trackEnabled !== null && profile.track_enabled !== trackEnabled) return false
    return true
  })
}

function sortProfiles(
  profiles: readonly AppProfileConfig[],
  filters: AppProfileListFilters
): AppProfileConfig[] {
  const sortBy = filters.sort_by ?? 'last_seen'
  const sortDirection = filters.sort_direction ?? (sortBy === 'name' ? 'asc' : 'desc')
  const direction = sortDirection === 'asc' ? 1 : -1

  return [...profiles].sort((left, right) => {
    const primary = compareProfiles(left, right, sortBy)
    if (primary !== 0) return primary * direction
    return compareProfileNames(left, right) || appProfileCollator.compare(left.app_key, right.app_key)
  })
}

function paginateProfiles(
  profiles: readonly AppProfileConfig[],
  page: number,
  pageSize: number
): AppProfileConfig[] {
  const safePage = Math.max(1, page)
  const safePageSize = Math.max(1, pageSize)
  const start = (safePage - 1) * safePageSize
  return profiles.slice(start, start + safePageSize)
}

function countProfiles(profiles: readonly AppProfileConfig[]): AppProfileCounts {
  return {
    all: profiles.length,
    classified: profiles.filter((profile) => profile.is_classified).length,
    unclassified: profiles.filter((profile) => !profile.is_classified).length,
    configured: profiles.filter((profile) => profile.is_configured).length,
    excluded: profiles.filter((profile) => !profile.track_enabled).length
  }
}

function profileMatchesKeyword(profile: AppProfileConfig, keyword: string): boolean {
  const haystack = [
    profile.app_key,
    profile.process_name,
    profile.display_name,
    profile.effective_display_name,
    profile.default_display_name,
    profile.category
  ]
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .join(' ')
    .toLocaleLowerCase()

  return haystack.includes(keyword)
}

function compareProfiles(
  left: AppProfileConfig,
  right: AppProfileConfig,
  sortBy: NonNullable<AppProfileListFilters['sort_by']>
): number {
  if (sortBy === 'name') {
    return compareProfileNames(left, right)
  }

  if (sortBy === 'duration') {
    return left.total_active_duration_sec - right.total_active_duration_sec
  }

  return String(left.last_seen_at ?? '').localeCompare(String(right.last_seen_at ?? ''))
}

function compareProfileNames(left: AppProfileConfig, right: AppProfileConfig): number {
  return appProfileCollator.compare(profileDisplayName(left), profileDisplayName(right))
}

function profileDisplayName(profile: AppProfileConfig): string {
  return profile.effective_display_name || profile.display_name || profile.default_display_name || profile.process_name
}
</script>

<template>
  <div class="app-profiles-root">

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
  grid-template-rows: minmax(0, 1fr);
  overflow: hidden;
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
</style>
