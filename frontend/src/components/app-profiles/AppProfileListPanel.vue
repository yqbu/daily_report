<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { Check, Delete, RefreshLeft } from '@element-plus/icons-vue'

import type { AppCategoryConfig, AppProfileConfig, SaveAppProfilePayload } from '../../api/types'

interface AppProfileDraft {
  displayName: string
  category: string
  color: string
  trackEnabled: boolean
  captureTitleEnabled: boolean
}

interface AppProfileSnapshot {
  displayName: string | null
  category: string | null
  color: string
  trackEnabled: boolean
  captureTitleEnabled: boolean
}

const props = defineProps<{
  profiles: AppProfileConfig[]
  categories: AppCategoryConfig[]
  total: number
  loading: boolean
  savingAppKey: string
  error?: string
}>()

const emit = defineEmits<{
  save: [payload: SaveAppProfilePayload]
  reset: [appKey: string]
  'delete-records': [appKey: string]
  'dirty-change': [dirty: boolean]
}>()

const drafts = reactive<Record<string, AppProfileDraft>>({})

const categoryOptions = computed(() => {
  const names = new Set<string>()
  const options: Array<{ name: string; color: string }> = []

  for (const category of props.categories) {
    if (!names.has(category.name)) {
      names.add(category.name)
      options.push({ name: category.name, color: category.color })
    }
  }

  for (const profile of props.profiles) {
    if (profile.category && !names.has(profile.category)) {
      names.add(profile.category)
      options.push({ name: profile.category, color: profile.category_color })
    }
  }

  return options.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})

const hasUnsavedChanges = computed(() => props.profiles.some((profile) => profileHasChanges(profile)))

watch(
  () => props.profiles,
  (profiles) => {
    const liveKeys = new Set<string>()
    for (const profile of profiles) {
      liveKeys.add(profile.app_key)
      drafts[profile.app_key] = createDraft(profile)
    }

    for (const key of Object.keys(drafts)) {
      if (!liveKeys.has(key)) {
        delete drafts[key]
      }
    }
  },
  { immediate: true }
)

watch(
  hasUnsavedChanges,
  (dirty) => {
    emit('dirty-change', dirty)
  },
  { immediate: true }
)

function createDraft(profile: AppProfileConfig): AppProfileDraft {
  return {
    displayName: profile.display_name ?? '',
    category: profile.category,
    color: profile.color ?? profile.effective_color,
    trackEnabled: profile.track_enabled,
    captureTitleEnabled: profile.capture_title_enabled
  }
}

function draftFor(profile: AppProfileConfig): AppProfileDraft {
  if (!drafts[profile.app_key]) {
    drafts[profile.app_key] = createDraft(profile)
  }
  return drafts[profile.app_key]
}

function saveProfile(profile: AppProfileConfig): void {
  if (!profileHasChanges(profile)) return

  emit('save', createSavePayload(profile))
}

function createSavePayload(profile: AppProfileConfig): SaveAppProfilePayload {
  const draft = draftFor(profile)

  return {
    app_key: profile.app_key,
    process_name: profile.process_name,
    exe_path: profile.exe_path,
    display_name: draft.displayName.trim() || null,
    category: draft.category || null,
    color: draft.color || null,
    track_enabled: draft.trackEnabled,
    capture_title_enabled: draft.captureTitleEnabled
  }
}

function resetDraft(profile: AppProfileConfig): void {
  drafts[profile.app_key] = createDraft(profile)
}

function resetAllDrafts(): void {
  for (const profile of props.profiles) {
    drafts[profile.app_key] = createDraft(profile)
  }
}

function getChangedPayloads(): SaveAppProfilePayload[] {
  return props.profiles.filter((profile) => profileHasChanges(profile)).map((profile) => createSavePayload(profile))
}

function profileHasChanges(profile: AppProfileConfig): boolean {
  const draft = drafts[profile.app_key]
  if (!draft) return false

  return serializeSnapshot(createDraftSnapshot(draft)) !== serializeSnapshot(createProfileSnapshot(profile))
}

function createDraftSnapshot(draft: AppProfileDraft): AppProfileSnapshot {
  return {
    displayName: normalizeOptionalText(draft.displayName),
    category: normalizeOptionalText(draft.category),
    color: normalizeColor(draft.color),
    trackEnabled: draft.trackEnabled,
    captureTitleEnabled: draft.captureTitleEnabled
  }
}

function createProfileSnapshot(profile: AppProfileConfig): AppProfileSnapshot {
  return {
    displayName: normalizeOptionalText(profile.display_name),
    category: normalizeOptionalText(profile.category),
    color: normalizeColor(profile.color ?? profile.effective_color),
    trackEnabled: profile.track_enabled,
    captureTitleEnabled: profile.capture_title_enabled
  }
}

function serializeSnapshot(snapshot: AppProfileSnapshot): string {
  return JSON.stringify(snapshot)
}

function normalizeOptionalText(value?: string | null): string | null {
  const normalized = value?.trim() ?? ''
  return normalized.length > 0 ? normalized : null
}

function normalizeColor(value?: string | null): string {
  return (value?.trim() || '#8F98A8').toUpperCase()
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0 分钟'

  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  if (hours <= 0) return `${minutes} 分钟`
  if (minutes <= 0) return `${hours} 小时`
  return `${hours} 小时 ${minutes} 分钟`
}

function formatLastSeen(value?: string | null): string {
  if (!value) return '尚未采集'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

defineExpose({
  hasUnsavedChanges,
  getChangedPayloads,
  resetAllDrafts
})
</script>

<template>
  <section class="list-panel">
    <header class="list-header">
      <div class="list-heading">
        <p class="list-kicker">配置展示</p>
        <h2 class="list-title">应用配置列表</h2>
        <p class="list-subtitle">共 {{ total }} 个应用，列表区域独立滚动。</p>
      </div>

      <div v-if="$slots.actions" class="list-actions">
        <slot name="actions" />
      </div>
    </header>

    <div class="list-scroll" v-loading="loading">
      <table v-if="profiles.length > 0" class="profile-table">
        <thead>
          <tr>
            <th class="column-app">应用</th>
            <th class="column-name">显示名</th>
            <th class="column-category">分类</th>
            <th class="column-color">颜色</th>
            <th class="column-switches">采集</th>
            <th class="column-usage">记录</th>
            <th class="column-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="profile in profiles"
            :key="profile.app_key"
            :class="{
              'profile-row--excluded': !draftFor(profile).trackEnabled,
              'profile-row--dirty': profileHasChanges(profile)
            }"
          >
            <td class="app-cell">
              <div class="app-identity">
                <span class="app-swatch" :style="{ backgroundColor: draftFor(profile).color }"></span>
                <div class="app-copy">
                  <strong class="app-name">{{ profile.effective_display_name }}</strong>
                  <span class="app-process">{{ profile.process_name }}</span>
                  <span class="app-title">{{ profile.sample_window_title || '未采集窗口标题' }}</span>
                </div>
              </div>
            </td>

            <td>
              <input
                v-model="draftFor(profile).displayName"
                class="text-input"
                type="text"
                autocomplete="off"
                :placeholder="profile.default_display_name"
                @keydown.enter.prevent="saveProfile(profile)"
              />
            </td>

            <td>
              <select v-model="draftFor(profile).category" class="select-input">
                <option v-for="category in categoryOptions" :key="category.name" :value="category.name">
                  {{ category.name }}
                </option>
              </select>
            </td>

            <td>
              <div class="color-editor">
                <input v-model="draftFor(profile).color" class="color-input" type="color" />
                <span class="color-value">{{ draftFor(profile).color }}</span>
              </div>
            </td>

            <td>
              <div class="switch-stack">
                <label class="toggle-row">
                  <input v-model="draftFor(profile).trackEnabled" type="checkbox" />
                  <span>统计</span>
                </label>
                <label class="toggle-row">
                  <input v-model="draftFor(profile).captureTitleEnabled" type="checkbox" />
                  <span>标题</span>
                </label>
              </div>
            </td>

            <td>
              <div class="usage-copy">
                <strong>{{ formatDuration(profile.total_active_duration_sec) }}</strong>
                <span>{{ profile.session_count }} 次 · {{ formatLastSeen(profile.last_seen_at) }}</span>
              </div>
            </td>

            <td>
              <div class="row-actions">
                <button
                  class="row-button row-button--primary"
                  type="button"
                  title="保存配置"
                  :disabled="savingAppKey === profile.app_key || !profileHasChanges(profile)"
                  @click="saveProfile(profile)"
                >
                  <Check class="row-button-icon" />
                </button>
                <button
                  class="row-button"
                  type="button"
                  title="恢复默认配置"
                  :disabled="savingAppKey === profile.app_key"
                  @click="emit('reset', profile.app_key)"
                >
                  <RefreshLeft class="row-button-icon" />
                </button>
                <button
                  class="row-button row-button--danger"
                  type="button"
                  title="移除该应用历史记录"
                  :disabled="savingAppKey === profile.app_key"
                  @click="emit('delete-records', profile.app_key)"
                >
                  <Delete class="row-button-icon" />
                </button>
                <button
                  class="row-button"
                  type="button"
                  title="放弃本行未保存修改"
                  :disabled="savingAppKey === profile.app_key || !profileHasChanges(profile)"
                  @click="resetDraft(profile)"
                >
                  重置
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else class="empty-state">
        <p class="empty-title">暂无应用配置</p>
        <p class="empty-description">启动采集器后，这里会显示已观察到的应用；也可以通过分类面板先维护分类。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.list-panel {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.list-header {
  min-width: 0;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid #e6ebf3;
  background: #fbfdff;
}

.list-heading {
  min-width: 0;
}

.list-kicker,
.list-title,
.list-subtitle,
.empty-title,
.empty-description {
  margin: 0;
}

.list-kicker {
  color: #16a34a;
  font-size: 12px;
  font-weight: 780;
  line-height: 1.2;
}

.list-title {
  margin-top: 4px;
  color: #172033;
  font-size: 19px;
  font-weight: 820;
  line-height: 1.2;
}

.list-subtitle {
  margin-top: 5px;
  color: #667085;
  font-size: 13px;
}

.list-actions {
  flex: 0 0 auto;
}

.list-scroll {
  min-height: 0;
  overflow: auto;
}

.profile-table {
  width: 100%;
  min-width: 1120px;
  border-collapse: separate;
  border-spacing: 0;
}

.profile-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  height: 42px;
  padding: 0 14px;
  border-bottom: 1px solid #e6ebf3;
  color: #667085;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 780;
  text-align: left;
}

.profile-table td {
  min-width: 0;
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f7;
  vertical-align: middle;
}

.profile-table tr:hover td {
  background: #fbfdff;
}

.profile-row--excluded td {
  background: #fcfcfd;
}

.profile-row--dirty td {
  background: #fffdf5;
}

.profile-row--dirty td:first-child {
  box-shadow: inset 3px 0 0 #f59e0b;
}

.column-app {
  width: 280px;
}

.column-name {
  width: 190px;
}

.column-category {
  width: 150px;
}

.column-color {
  width: 150px;
}

.column-switches {
  width: 124px;
}

.column-usage {
  width: 190px;
}

.column-actions {
  width: 172px;
}

.app-identity {
  min-width: 0;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}

.app-swatch {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.12);
}

.app-copy {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.app-name,
.app-process,
.app-title,
.usage-copy span,
.color-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-name {
  color: #172033;
  font-size: 14px;
  font-weight: 780;
}

.app-process,
.app-title,
.usage-copy span {
  color: #667085;
  font-size: 12px;
}

.text-input,
.select-input {
  width: 100%;
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  outline: 0;
  color: #172033;
  background: #ffffff;
  font-size: 13px;
}

.text-input:focus,
.select-input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.color-editor {
  min-width: 0;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.color-input {
  width: 34px;
  height: 34px;
  padding: 2px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #ffffff;
  cursor: pointer;
}

.color-value {
  color: #526179;
  font-size: 12px;
  font-family: "Segoe UI Mono", "Consolas", monospace;
}

.switch-stack {
  display: grid;
  gap: 6px;
}

.toggle-row {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #344054;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.toggle-row input {
  width: 15px;
  height: 15px;
  accent-color: #2563eb;
}

.usage-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.usage-copy strong {
  color: #172033;
  font-size: 13px;
  font-weight: 780;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.row-button {
  height: 30px;
  min-width: 30px;
  display: inline-grid;
  place-items: center;
  padding: 0 8px;
  border: 1px solid #dce3ee;
  border-radius: 7px;
  color: #526179;
  background: #ffffff;
  font-size: 12px;
  font-weight: 720;
  cursor: pointer;
}

.row-button:hover {
  color: #2563eb;
  border-color: #c9dcff;
  background: #eff6ff;
}

.row-button--primary {
  color: #047857;
  border-color: #bbf7d0;
  background: #ecfdf5;
}

.row-button--danger:hover {
  color: #b42318;
  border-color: #fecaca;
  background: #fef2f2;
}

.row-button:disabled {
  cursor: wait;
  opacity: 0.54;
}

.row-button-icon {
  width: 15px;
  height: 15px;
}

.empty-state {
  height: 100%;
  min-height: 180px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 8px;
  padding: 28px;
  text-align: center;
}

.empty-title {
  color: #172033;
  font-size: 16px;
  font-weight: 780;
}

.empty-description {
  max-width: 420px;
  color: #667085;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 760px) {
  .list-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
