<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'

import { callTypedBridge } from '../api/bridge'
import type {
  AppCategoryConfig,
  AppProfileConfig,
  AppProfileListFilters,
  AppProfileListPayload,
  SaveAppProfilePayload
} from '../api/types'
import FeaturePlaceholder from '../components/FeaturePlaceholder.vue'
import PageLayout from '../layouts/PageLayout.vue'

const appProfileFilters = shallowRef<AppProfileListFilters>({
  classification: 'all',
  keyword: ''
})
const appProfilePage = shallowRef(1)
const appProfilePageSize = shallowRef(100)
const appProfiles = shallowRef<AppProfileListPayload>(emptyAppProfileList())
const appCategories = shallowRef<AppCategoryConfig[]>([])
const appProfileLoading = shallowRef(false)
const appProfileError = shallowRef('')

const appProfileSummary = computed(() => appProfiles.value.counts)

const sections = computed(() => [
  {
    title: '应用列表数据',
    description: `已准备 listAppProfiles，当前可读取 ${appProfileSummary.value.all} 个应用配置候选。`
  },
  {
    title: '应用覆盖配置',
    description: '已准备 saveAppProfile、resetAppProfile，用于保存显示名、分类、颜色、图标和标题采集开关。'
  },
  {
    title: '分类与颜色',
    description: `已准备分类接口，当前可读取 ${appCategories.value.length} 个分类。`
  },
  {
    title: '历史记录维护',
    description: '已准备 deleteAppRecords，用于按 exe 软删除对应应用历史记录。'
  }
])

async function loadAppProfileBootstrap(): Promise<void> {
  appProfileLoading.value = true
  appProfileError.value = ''
  try {
    const [profilesPayload, categoriesPayload] = await Promise.all([
      callTypedBridge('listAppProfiles', {
        filters: appProfileFilters.value,
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

async function saveAppProfileDraft(payload: SaveAppProfilePayload): Promise<AppProfileConfig> {
  const saved = await callTypedBridge('saveAppProfile', payload)
  await loadAppProfileBootstrap()
  return saved
}

async function resetAppProfileDraft(appKey: string): Promise<AppProfileConfig> {
  const reset = await callTypedBridge('resetAppProfile', { app_key: appKey })
  await loadAppProfileBootstrap()
  return reset
}

async function deleteAppProfileRecords(appKey: string): Promise<number> {
  const result = await callTypedBridge('deleteAppRecords', { app_key: appKey })
  await loadAppProfileBootstrap()
  return result.deleted_count
}

async function saveAppCategoryDraft(name: string, color: string): Promise<AppCategoryConfig> {
  const saved = await callTypedBridge('saveAppCategory', { name, color })
  await loadAppProfileBootstrap()
  return saved
}

async function deleteAppCategoryDraft(name: string): Promise<void> {
  await callTypedBridge('deleteAppCategory', { name, fallback_category: '其他' })
  await loadAppProfileBootstrap()
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
  void loadAppProfileBootstrap()
})

function emptyAppProfileList(): AppProfileListPayload {
  return {
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
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
  <PageLayout title="应用配置" subtitle="按应用维护名称、分类、颜色、图标和记录策略。" scrollable>
    <FeaturePlaceholder
      :icon="MagicStick"
      title="应用配置界面"
      :description="appProfileError || (appProfileLoading ? '正在加载应用配置数据。' : '后端接口和页面数据入口已准备，后续可在这里实现完整配置界面。')"
      :sections="sections"
    />
  </PageLayout>
</template>
