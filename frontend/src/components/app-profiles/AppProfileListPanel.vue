<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, reactive, shallowRef, watch} from 'vue'
import {ElCard, ElIcon, ElInput, ElMessage, ElMessageBox, ElOption, ElSelect, ElSwitch, ElTooltip} from 'element-plus'
import {Check, Close, Delete, Edit, RefreshLeft} from '@element-plus/icons-vue'

import type {AppCategoryConfig, AppProfileConfig, SaveAppProfilePayload} from '../../api/types'

interface AppProfileDraft {
  displayName: string
  category: string
  color: string
  iconPath: string | null
  iconDataUrl: string
  iconFileName: string
  trackEnabled: boolean
  captureTitleEnabled: boolean
}

interface AppProfileSnapshot {
  displayName: string | null
  category: string | null
  color: string
  iconPath: string | null
  iconDataUrl: string | null
  trackEnabled: boolean
  captureTitleEnabled: boolean
}

interface AppProfileCardState {
  key: string
  profile: AppProfileConfig
  draft: AppProfileDraft
  dirty: boolean
  excluded: boolean
  displayName: string
  iconSrc: string
  initial: string
  cardStyle: Record<string, string>
}

interface DisplayNameEditState {
  value: string
}

const props = defineProps<{
  profiles: AppProfileConfig[]
  categories: AppCategoryConfig[]
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
const displayNameEdits = reactive<Record<string, DisplayNameEditState>>({})

const categoryOptions = computed(() => {
  const names = new Set<string>()
  const options: Array<{ name: string; color: string }> = []

  for (const category of props.categories) {
    if (!names.has(category.name)) {
      names.add(category.name)
      options.push({name: category.name, color: category.color})
    }
  }

  for (const profile of props.profiles) {
    if (profile.category && !names.has(profile.category)) {
      names.add(profile.category)
      options.push({name: profile.category, color: profile.category_color})
    }
  }

  return options.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})

const categoryColorMap = computed(() => {
  return new Map(categoryOptions.value.map((category) => [category.name, normalizeColor(category.color)]))
})

const hasUnsavedChanges = computed(() => props.profiles.some((profile) => profileHasChanges(profile)))

const profileCards = computed<AppProfileCardState[]>(() => {
  return props.profiles.map((profile, index) => {
    const draft = readDraftFor(profile)
    return {
      key: profile.app_key,
      profile,
      draft,
      dirty: profileHasChanges(profile),
      excluded: !draft.trackEnabled,
      displayName: displayNameFor(profile, draft),
      iconSrc: iconSource(profile, draft),
      initial: appInitial(profile, draft),
      cardStyle: profileCardStyle(draft, index)
    }
  })
})
const profileListSignature = computed(() => props.profiles.map((profile) => profile.app_key).join('|') || 'empty')
const profileCardStaggering = shallowRef(false)
let profileCardAnimationFrame = 0
let profileCardAnimationTimer = 0
let lastCopiedExecutableKey = ''
let lastCopiedExecutableAt = 0

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

      for (const key of Object.keys(displayNameEdits)) {
        if (!liveKeys.has(key)) {
          delete displayNameEdits[key]
        }
      }
    },
    {immediate: true}
)

watch(
    hasUnsavedChanges,
    (dirty) => {
      emit('dirty-change', dirty)
    },
    {immediate: true}
)

watch(
    profileListSignature,
    () => {
      triggerProfileCardStagger()
    },
    {flush: 'post'}
)

onMounted(() => {
  triggerProfileCardStagger()
})

onBeforeUnmount(() => {
  window.cancelAnimationFrame(profileCardAnimationFrame)
  window.clearTimeout(profileCardAnimationTimer)
})

function triggerProfileCardStagger(): void {
  window.cancelAnimationFrame(profileCardAnimationFrame)
  window.clearTimeout(profileCardAnimationTimer)
  profileCardStaggering.value = false

  if (profileCards.value.length <= 0) return

  profileCardAnimationFrame = window.requestAnimationFrame(() => {
    profileCardAnimationFrame = window.requestAnimationFrame(() => {
      profileCardStaggering.value = true
      profileCardAnimationTimer = window.setTimeout(() => {
        profileCardStaggering.value = false
      }, 580 + Math.min(profileCards.value.length, 18) * 42)
    })
  })
}

function createDraft(profile: AppProfileConfig): AppProfileDraft {
  return {
    displayName: profile.display_name ?? '',
    category: profile.category,
    color: profile.color ?? profile.effective_color,
    iconPath: profile.icon_path ?? null,
    iconDataUrl: '',
    iconFileName: '',
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

function readDraftFor(profile: AppProfileConfig): AppProfileDraft {
  return drafts[profile.app_key] ?? createDraft(profile)
}

function saveProfile(profile: AppProfileConfig): void {
  if (!profileHasChanges(profile)) return

  emit('save', createSavePayload(profile))
}

function createSavePayload(profile: AppProfileConfig): SaveAppProfilePayload {
  const draft = draftFor(profile)
  const category = normalizeOptionalText(draft.category)
  const color = normalizeColor(draft.color)

  return {
    app_key: profile.app_key,
    process_name: profile.process_name,
    exe_path: profile.exe_path,
    display_name: draft.displayName.trim() || null,
    category,
    color: color === resolveCategoryColor(category) ? null : color,
    icon_data_url: draft.iconDataUrl || undefined,
    icon_file_name: draft.iconFileName || undefined,
    track_enabled: draft.trackEnabled,
    capture_title_enabled: draft.captureTitleEnabled
  }
}

function resetDraft(profile: AppProfileConfig): void {
  drafts[profile.app_key] = createDraft(profile)
  cancelDisplayNameEdit(profile.app_key)
}

async function copyExecutableDirectory(profile: AppProfileConfig): Promise<void> {
  const directory = executableDirectoryFor(profile)
  if (!directory) {
    ElMessage.warning('当前应用暂无可复制的可执行文件目录')
    return
  }

  const now = Date.now()
  if (lastCopiedExecutableKey === profile.app_key && now - lastCopiedExecutableAt < 500) return
  lastCopiedExecutableKey = profile.app_key
  lastCopiedExecutableAt = now

  try {
    await writeClipboardText(directory)
    ElMessage.success(`已复制目录：${directory}`)
  } catch {
    ElMessage.error('复制失败，请稍后重试')
  }
}

function copyExecutableDirectoryTooltip(profile: AppProfileConfig): string {
  return executableDirectoryFor(profile) ? '点击复制可执行文件所在目录' : '暂无可执行文件目录'
}

function executableDirectoryFor(profile: AppProfileConfig): string {
  const executablePath = profile.exe_path?.trim()
  if (!executablePath) return ''

  const normalizedPath = executablePath.replace(/[\\/]+$/, '')
  const separatorIndex = Math.max(normalizedPath.lastIndexOf('\\'), normalizedPath.lastIndexOf('/'))
  if (separatorIndex <= 0) return ''
  return normalizedPath.slice(0, separatorIndex)
}

async function writeClipboardText(text: string): Promise<void> {
  try {
    await window.navigator.clipboard.writeText(text)
    return
  } catch {
    fallbackCopyText(text)
  }
}

function fallbackCopyText(text: string): void {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)
  textarea.select()

  try {
    if (!document.execCommand('copy')) {
      throw new Error('copy command failed')
    }
  } finally {
    document.body.removeChild(textarea)
  }
}

async function confirmResetProfile(profile: AppProfileConfig): Promise<void> {
  const displayName = displayNameFor(profile, readDraftFor(profile))

  try {
    await ElMessageBox.confirm(
        `确定要将「${displayName}」恢复为默认配置吗？当前配置将被默认规则覆盖。`,
        '恢复默认配置',
        {
          type: 'warning',
          confirmButtonText: '恢复默认',
          cancelButtonText: '取消',
          autofocus: false
        }
    )
    emit('reset', profile.app_key)
  } catch {
    // User cancelled or closed the confirmation dialog.
  }
}

async function confirmDeleteProfileRecords(profile: AppProfileConfig): Promise<void> {
  const displayName = displayNameFor(profile, readDraftFor(profile))

  try {
    await ElMessageBox.confirm(
        `确定要删除「${displayName}」的应用历史记录吗？删除后无法撤销。`,
        '删除应用历史记录',
        {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          confirmButtonClass: 'el-button--danger',
          autofocus: false
        }
    )
    emit('delete-records', profile.app_key)
  } catch {
    // User cancelled or closed the confirmation dialog.
  }
}

function resetAllDrafts(): void {
  for (const profile of props.profiles) {
    drafts[profile.app_key] = createDraft(profile)
  }
  for (const appKey of Object.keys(displayNameEdits)) {
    delete displayNameEdits[appKey]
  }
}

function getChangedPayloads(): SaveAppProfilePayload[] {
  return props.profiles.filter((profile) => profileHasChanges(profile)).map((profile) => createSavePayload(profile))
}

function profileHasChanges(profile: AppProfileConfig): boolean {
  const draft = drafts[profile.app_key]
  if (!draft) return false

  return !snapshotsEqual(createDraftSnapshot(draft), createProfileSnapshot(profile))
}

function createDraftSnapshot(draft: AppProfileDraft): AppProfileSnapshot {
  return {
    displayName: normalizeOptionalText(draft.displayName),
    category: normalizeOptionalText(draft.category),
    color: normalizeColor(draft.color),
    iconPath: normalizeOptionalText(draft.iconPath),
    iconDataUrl: normalizeOptionalText(draft.iconDataUrl),
    trackEnabled: draft.trackEnabled,
    captureTitleEnabled: draft.captureTitleEnabled
  }
}

function createProfileSnapshot(profile: AppProfileConfig): AppProfileSnapshot {
  return {
    displayName: normalizeOptionalText(profile.display_name),
    category: normalizeOptionalText(profile.category),
    color: normalizeColor(profile.color ?? profile.effective_color),
    iconPath: normalizeOptionalText(profile.icon_path),
    iconDataUrl: null,
    trackEnabled: profile.track_enabled,
    captureTitleEnabled: profile.capture_title_enabled
  }
}

function snapshotsEqual(left: AppProfileSnapshot, right: AppProfileSnapshot): boolean {
  return (
      left.displayName === right.displayName &&
      left.category === right.category &&
      left.color === right.color &&
      left.iconPath === right.iconPath &&
      left.iconDataUrl === right.iconDataUrl &&
      left.trackEnabled === right.trackEnabled &&
      left.captureTitleEnabled === right.captureTitleEnabled
  )
}

function normalizeOptionalText(value?: string | null): string | null {
  const normalized = value?.trim() ?? ''
  return normalized.length > 0 ? normalized : null
}

function normalizeColor(value?: string | null): string {
  return (value?.trim() || '#8F98A8').toUpperCase()
}

function resolveCategoryColor(categoryName?: string | null): string {
  if (!categoryName) return '#8F98A8'
  return categoryColorMap.value.get(categoryName) ?? '#8F98A8'
}

function handleCategoryChange(profile: AppProfileConfig, categoryName: string): void {
  const draft = draftFor(profile)
  draft.category = categoryName
  draft.color = resolveCategoryColor(categoryName)
}

function startDisplayNameEdit(profile: AppProfileConfig, draft: AppProfileDraft): void {
  displayNameEdits[profile.app_key] = {
    value: draft.displayName.trim() || profile.effective_display_name || profile.default_display_name || profile.process_name
  }
}

function confirmDisplayNameEdit(profile: AppProfileConfig): void {
  const editState = displayNameEdits[profile.app_key]
  if (!editState) return

  draftFor(profile).displayName = editState.value.trim()
  delete displayNameEdits[profile.app_key]
}

async function handleIconFileChange(profile: AppProfileConfig, event: Event): Promise<void> {
  const input = event.target as HTMLInputElement | null
  const file = input?.files?.[0]
  if (!input || !file) return

  try {
    const dataUrl = await readFileAsDataUrl(file)
    const draft = draftFor(profile)
    draft.iconDataUrl = dataUrl
    draft.iconFileName = file.name
  } finally {
    input.value = ''
  }
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.addEventListener('load', () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result)
        return
      }
      reject(new Error('无法读取图标文件'))
    })
    reader.addEventListener('error', () => {
      reject(reader.error ?? new Error('无法读取图标文件'))
    })
    reader.readAsDataURL(file)
  })
}

function cancelDisplayNameEdit(appKey: string): void {
  delete displayNameEdits[appKey]
}

function isDisplayNameEditing(appKey: string): boolean {
  return displayNameEdits[appKey] !== undefined
}

function displayNameFor(profile: AppProfileConfig, draft: AppProfileDraft): string {
  return draft.displayName.trim() || profile.effective_display_name || profile.default_display_name || profile.process_name
}

function profileCardStyle(draft: AppProfileDraft, index: number): Record<string, string> {
  const color = normalizeColor(draft.color)
  return {
    '--profile-color': color,
    '--profile-color-soft': hexToRgba(color, 0.1),
    '--profile-card-rise-delay': `${Math.min(index, 18) * 42}ms`
  }
}

function iconSource(profile: AppProfileConfig, draft: AppProfileDraft): string {
  if (draft.iconDataUrl) return draft.iconDataUrl
  if (profile.icon_url) return profile.icon_url

  const icon = profile.icon_base64?.trim()
  if (!icon) return ''
  return icon.startsWith('data:') ? icon : `data:image/png;base64,${icon}`
}

function appInitial(profile: AppProfileConfig, draft: AppProfileDraft): string {
  const name = displayNameFor(profile, draft) || profile.process_name || profile.app_key
  return name.trim().slice(0, 1).toUpperCase() || 'A'
}

function hexToRgba(hex: string, alpha: number): string {
  const normalized = normalizeColor(hex).replace('#', '')
  const red = Number.parseInt(normalized.slice(0, 2), 16)
  const green = Number.parseInt(normalized.slice(2, 4), 16)
  const blue = Number.parseInt(normalized.slice(4, 6), 16)
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
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
    <div class="list-scroll" :class="{ 'list-scroll--loading': loading }" :aria-busy="loading">
      <div
          v-if="profileCards.length > 0"
          class="profile-card-grid"
          :class="{ 'profile-card-grid--stagger': profileCardStaggering }"
      >
        <el-card
            v-for="card in profileCards"
            :key="card.key"
            class="profile-card"
            :class="{
              'profile-card--excluded': card.excluded,
              'profile-card--dirty': card.dirty
            }"
            shadow="never"
            :body-style="{ padding: '0' }"
            :style="card.cardStyle"
        >
          <div class="profile-card-body">
            <header class="profile-card-header">
              <div class="app-identity">
                <span
                    class="app-avatar app-avatar--clickable"
                    :class="{
                      'app-avatar--has-icon': card.iconSrc
                    }"
                    title="设置或更换应用图标"
                >
                  <img
                      v-if="card.iconSrc"
                      class="app-icon"
                      :src="card.iconSrc"
                      alt=""
                  />
                  <span v-else class="app-initial">{{ card.initial }}</span>
                  <input
                      class="icon-file-input"
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/x-icon"
                      @change="handleIconFileChange(card.profile, $event)"
                  />
                </span>

                <div class="identity-main">
                  <Transition name="display-name-edit" mode="out-in">
                    <div v-if="isDisplayNameEditing(card.profile.app_key)" class="display-name-editor">
                      <el-input
                          v-model="displayNameEdits[card.profile.app_key].value"
                          class="display-name-input"
                          type="text"
                          autocomplete="off"
                          :placeholder="card.displayName"
                          @keydown.enter.prevent="confirmDisplayNameEdit(card.profile)"
                          @keydown.esc.prevent="cancelDisplayNameEdit(card.profile.app_key)"
                      />
                      <span class="identity-action-slot">
                        <el-tooltip content="确认显示名称" placement="top" :show-after="80" :hide-after="0">
                          <button
                              class="identity-action identity-action--confirm"
                              type="button"
                              aria-label="确认显示名称"
                              @click="confirmDisplayNameEdit(card.profile)"
                          >
                            <Check class="identity-action-icon"/>
                          </button>
                        </el-tooltip>
                      </span>
                      <span class="identity-action-slot">
                        <el-tooltip content="取消编辑显示名称" placement="top" :show-after="80" :hide-after="0">
                          <button
                              class="identity-action"
                              type="button"
                              aria-label="取消编辑显示名称"
                              @click="cancelDisplayNameEdit(card.profile.app_key)"
                          >
                            <Close class="identity-action-icon"/>
                          </button>
                        </el-tooltip>
                      </span>
                    </div>

                    <div v-else class="app-copy">
                      <strong class="app-name">{{ card.displayName }}</strong>
                      <el-tooltip
                          :content="copyExecutableDirectoryTooltip(card.profile)"
                          placement="top"
                          :show-after="120"
                          :hide-after="0"
                      >
                        <span
                            class="app-process app-process--copyable"
                            role="button"
                            tabindex="0"
                            @click.stop="copyExecutableDirectory(card.profile)"
                            @dblclick.stop.prevent="copyExecutableDirectory(card.profile)"
                            @keydown.enter.prevent="copyExecutableDirectory(card.profile)"
                            @keydown.space.prevent="copyExecutableDirectory(card.profile)"
                        >
                          {{ card.profile.process_name }}
                        </span>
                      </el-tooltip>
                    </div>
                  </Transition>
                </div>

                <span
                    class="identity-action-slot"
                    :class="{ 'identity-action--hidden': isDisplayNameEditing(card.profile.app_key) }"
                >
                  <el-tooltip content="编辑显示名称" placement="top" :show-after="80" :hide-after="0">
                    <button
                        class="identity-action"
                        type="button"
                        aria-label="编辑显示名称"
                        @click="startDisplayNameEdit(card.profile, card.draft)"
                    >
                      <el-icon>
                        <Edit/>
                      </el-icon>
                    </button>
                  </el-tooltip>
                </span>
              </div>
            </header>

            <div class="config-grid">
              <label class="field">
                <span class="field-label">分类</span>
                <el-select
                    v-model="card.draft.category"
                    class="profile-category-select"
                    popper-class="profile-category-popper"
                    fit-input-width
                    @change="handleCategoryChange(card.profile, $event)"
                >
                  <el-option
                      v-for="category in categoryOptions"
                      :key="category.name"
                      :label="category.name"
                      :value="category.name"
                  />
                </el-select>
              </label>

              <label class="field">
                <span class="field-label">颜色</span>
                <div class="color-editor">
                  <input v-model="card.draft.color" class="color-input" type="color"/>
                  <span class="color-value">{{ normalizeColor(card.draft.color) }}</span>
                </div>
              </label>

              <div class="field switch-field">
                <span class="field-label">采集选项</span>
                <div class="switch-inline-group">
                  <label class="switch-row">
                    <span>统计</span>
                    <el-switch v-model="card.draft.trackEnabled" size="small"/>
                  </label>
                  <label class="switch-row">
                    <span>标题</span>
                    <el-switch v-model="card.draft.captureTitleEnabled" size="small"/>
                  </label>
                </div>
              </div>
            </div>

            <footer class="profile-card-footer">
              <div class="usage-copy">
                <strong>{{ formatDuration(card.profile.total_active_duration_sec) }}</strong>
                <span>{{ card.profile.session_count }} 次 · {{ formatLastSeen(card.profile.last_seen_at) }}</span>
              </div>

              <div class="row-actions">
                <button
                    class="row-button row-button--primary"
                    type="button"
                    title="保存配置"
                    :disabled="savingAppKey === card.profile.app_key || !card.dirty"
                    @click="saveProfile(card.profile)"
                >
                  <Check class="row-button-icon"/>
                </button>
                <button
                    class="row-button"
                    type="button"
                    title="恢复默认配置"
                    :disabled="savingAppKey === card.profile.app_key"
                    @click="confirmResetProfile(card.profile)"
                  >
                    <RefreshLeft class="row-button-icon"/>
                  </button>
                <button
                    class="row-button row-button--danger"
                    type="button"
                    title="移除该应用历史记录"
                    :disabled="savingAppKey === card.profile.app_key"
                    @click="confirmDeleteProfileRecords(card.profile)"
                  >
                    <Delete class="row-button-icon"/>
                  </button>
                <button
                    class="row-button"
                    type="button"
                    title="放弃本卡片未保存修改"
                    :disabled="savingAppKey === card.profile.app_key || !card.dirty"
                    @click="resetDraft(card.profile)"
                >
                  <Close class="row-button-icon"/>
                </button>
              </div>
            </footer>
          </div>
        </el-card>
      </div>

      <div
          v-else-if="!loading"
          class="empty-state"
          :class="{ 'empty-state--rise': profileCardStaggering }"
      >
        <p class="empty-title">暂无应用配置</p>
        <p class="empty-description">启动采集器后，这里会显示已观察到的应用；也可以通过分类面板先维护分类。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.list-panel {
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: block;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.empty-title,
.empty-description {
  margin: 0;
}

.list-scroll {
  position: relative;
  height: 100%;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  background: #ffffff;
}

.list-scroll--loading {
  cursor: progress;
}

.list-loading-indicator {
  position: sticky;
  z-index: 3;
  top: 12px;
  width: fit-content;
  max-width: calc(100% - 32px);
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin: 12px 0 0 16px;
  padding: 0 12px;
  border: 1px solid #dce3ee;
  border-radius: 999px;
  color: #526179;
  background: #ffffff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  font-size: 12px;
  font-weight: 720;
  pointer-events: none;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  flex: 0 0 auto;
  border: 2px solid #bfdbfe;
  border-top-color: #2563eb;
  border-radius: 999px;
  animation: profile-loading-spin 760ms linear infinite;
}

.profile-loading-enter-active,
.profile-loading-leave-active {
  transition: opacity 220ms ease,
  transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.profile-loading-enter-from,
.profile-loading-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.profile-card-grid {
  width: 100%;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
  align-items: start;
  align-content: start;
  gap: 14px;
  padding: 16px;
}

.profile-card {
  --profile-color: #8F98A8;
  --profile-color-soft: rgba(143, 152, 168, 0.1);
  min-width: 0;
  border-color: #e1e7f0;
  border-radius: 8px;
  background: linear-gradient(90deg, var(--profile-color-soft), rgba(255, 255, 255, 0) 42%), #ffffff;
  overflow: hidden;
}

.profile-card-grid--stagger .profile-card {
  animation: profile-card-rise 560ms cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--profile-card-rise-delay, 0ms);
  will-change: opacity, transform;
}

.empty-state--rise {
  animation: profile-panel-rise 560ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.profile-card--dirty {
  border-color: #f59e0b;
  box-shadow: inset 3px 0 0 #f59e0b;
}

.profile-card--excluded {
  background: linear-gradient(90deg, rgba(148, 163, 184, 0.1), rgba(255, 255, 255, 0) 42%),
  #fbfcfe;
}

.profile-card-body {
  min-width: 0;
  display: grid;
  gap: 13px;
  padding: 15px;
}

.profile-card-header,
.profile-card-footer {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.profile-card-footer {
  align-items: flex-end;
  padding-top: 2px;
}

.app-identity {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 30px;
  align-items: center;
  gap: 10px;
}

.app-avatar {
  position: relative;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
  background: var(--profile-color);
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.12);
  overflow: hidden;
  margin-right: 10px;
}

.app-avatar--clickable {
  cursor: pointer;
}

.app-avatar--has-icon {
  background: transparent;
  box-shadow: none;
  overflow: hidden;
  padding: 3px;
}

.icon-file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.app-icon {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.app-initial {
  font-size: 15px;
  font-weight: 820;
  line-height: 1;
}

.app-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
  margin-left: 5px;
}

.identity-main {
  min-width: 0;
  min-height: 38px;
  display: grid;
  align-items: center;
  overflow: hidden;
}

.display-name-editor {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 30px 30px;
  align-items: center;
  gap: 6px;
  margin-left: 8px;
}

.display-name-input {
  min-width: 0;
  width: 100%;
}

:deep(.display-name-input .el-input__wrapper) {
  min-height: 32px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #c9dcff inset,
  0 0 0 3px rgba(37, 99, 235, 0.08);
}

:deep(.display-name-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #93c5fd inset,
  0 0 0 3px rgba(37, 99, 235, 0.14);
}

.identity-action {
  width: 30px;
  height: 30px;
  display: inline-grid;
  place-items: center;
  border: 1px solid #dce3ee;
  border-radius: 7px;
  color: #526179;
  background: #ffffff;
  cursor: pointer;
}

.identity-action-slot {
  width: 30px;
  height: 30px;
  display: inline-grid;
  place-items: center;
}

.identity-action:hover {
  color: #2563eb;
  border-color: #c9dcff;
  background: #eff6ff;
}

.identity-action--confirm {
  color: #047857;
  border-color: #bbf7d0;
  background: #ecfdf5;
}

.identity-action--hidden {
  visibility: hidden;
  pointer-events: none;
}

.identity-action-icon {
  width: 15px;
  height: 15px;
}

.display-name-edit-enter-active,
.display-name-edit-leave-active {
  overflow: hidden;
  transition: opacity 180ms ease,
  transform 180ms ease;
}

.display-name-edit-enter-from,
.display-name-edit-leave-to {
  opacity: 0;
  transform: translateX(-6px);
}

.display-name-edit-enter-to,
.display-name-edit-leave-from {
  opacity: 1;
  transform: translateX(0);
}

.app-name,
.app-process,
.usage-copy span,
.color-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-name {
  color: #172033;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.2;
}

.app-process,
.usage-copy span {
  color: #667085;
  font-size: 12px;
}

.app-process--copyable {
  display: block;
  max-width: 100%;
  border-radius: 5px;
  cursor: pointer;
  transition: color 160ms ease, background-color 160ms ease;
}

.app-process--copyable:hover,
.app-process--copyable:focus-visible {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
  outline: none;
}

.config-grid {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(112px, 0.42fr);
  gap: 11px;
}

.field,
.switch-field {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.switch-field {
  grid-column: 1 / -1;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  min-height: 34px;
  gap: 14px;
}

.switch-field .field-label {
  white-space: nowrap;
}

.field-label {
  color: #667085;
  font-size: 12px;
  font-weight: 740;
  line-height: 1;
}

.profile-category-select {
  width: 100%;
  min-width: 0;
}

:deep(.profile-category-select .el-select__wrapper) {
  min-height: 34px;
  padding: 0 10px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dce3ee inset;
  font-size: 13px;
}

:deep(.profile-category-select .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #93c5fd inset,
  0 0 0 3px rgba(37, 99, 235, 0.12);
}

:deep(.profile-category-select .el-select__selected-item) {
  color: #172033;
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

.switch-inline-group {
  min-width: 0;
  height: 34px;
  display: flex;
  align-items: center;
  gap: 18px;
}

.switch-row {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 7px;
  color: #344054;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
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
  justify-content: flex-end;
  flex-wrap: wrap;
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
  cursor: not-allowed;
  opacity: 0.54;
}

.row-button:disabled:hover {
  color: #526179;
  border-color: #dce3ee;
  background: #ffffff;
}

.row-button--primary:disabled:hover {
  color: #047857;
  border-color: #bbf7d0;
  background: #ecfdf5;
}

.row-button-icon {
  width: 15px;
  height: 15px;
}

:deep(.el-switch__core) {
  min-width: 32px;
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

@keyframes profile-loading-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes profile-panel-rise {
  from {
    opacity: 0.72;
    transform: translateY(16px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes profile-card-rise {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.995);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-spinner,
  .profile-card-grid--stagger .profile-card,
  .empty-state--rise,
  .profile-loading-enter-active,
  .profile-loading-leave-active {
    animation: none;
    transition: none;
  }
}

@media (max-width: 760px) {
  .profile-card-grid {
    grid-template-columns: minmax(0, 1fr);
    padding: 12px;
  }

  .profile-card-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .row-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 520px) {
  .config-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .switch-inline-group {
    flex-wrap: wrap;
    height: auto;
  }
}

@container (max-width: 360px) {
  .config-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .switch-field {
    grid-template-columns: minmax(0, 1fr);
  }

  .switch-inline-group {
    flex-wrap: wrap;
    height: auto;
  }
}
</style>
