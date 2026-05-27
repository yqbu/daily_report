<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Calendar, Check, Close, Connection, Refresh, Search } from '@element-plus/icons-vue'

import { useAppStore } from '../stores/app'

const route = useRoute()
const appStore = useAppStore()

const pageTitle = computed(() => String(route.meta.title || 'Daily Report'))
const showConfigActions = computed(() => appStore.topBar.mode === 'app-config')
const topBarStatusClass = computed(() => `save-status--${appStore.topBar.statusTone}`)
const topBarStatusText = computed(() => appStore.topBar.statusText || '已保存')
const todayLabel = new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  weekday: 'short'
}).format(new Date())
</script>

<template>
  <header class="top-bar">
    <div class="title-block">
      <span class="workspace-label">Daily Report</span>
      <h1 class="page-title">{{ pageTitle }}</h1>
    </div>

    <div v-if="showConfigActions" class="top-actions top-actions--config">
      <button
        v-if="appStore.topBar.canRefresh"
        class="top-button"
        type="button"
        :disabled="appStore.topBar.refreshing || appStore.topBar.saving"
        title="刷新当前页面数据"
        @click="appStore.requestTopBarRefresh()"
      >
        <Refresh class="action-icon" :class="{ 'action-icon--spin': appStore.topBar.refreshing }" />
        <span>刷新</span>
      </button>
      <span class="save-status" :class="topBarStatusClass">{{ topBarStatusText }}</span>
      <span class="top-action-divider" aria-hidden="true"></span>
      <button
        class="top-button"
        type="button"
        :disabled="!appStore.topBar.canCancel || appStore.topBar.saving"
        @click="appStore.requestTopBarCancel()"
      >
        <Close class="action-icon" />
        <span>取消</span>
      </button>
      <button
        class="top-button top-button--primary"
        type="button"
        :disabled="!appStore.topBar.canSave || appStore.topBar.saving"
        @click="appStore.requestTopBarSave()"
      >
        <Check class="action-icon" />
        <span>保存</span>
      </button>
    </div>

    <div v-else class="top-actions">
      <div class="search-pill" title="全局检索入口">
        <Search class="action-icon" />
        <span class="search-text">本地数据工作台</span>
      </div>

      <div class="info-pill" title="当前日期">
        <Calendar class="action-icon" />
        <span>{{ todayLabel }}</span>
      </div>

      <div class="info-pill info-pill--online" title="PySide6 QWebChannel">
        <Connection class="action-icon" />
        <span>Bridge</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
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
  gap: 10px;
}

.top-actions--config {
  gap: 8px;
}

.search-pill,
.info-pill,
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
  color: #526179;
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
  color: #526179;
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

.search-pill {
  min-width: 218px;
  justify-content: flex-start;
}

.info-pill--online {
  color: #047857;
  background: #ecfdf5;
  border-color: #bbf7d0;
}

.action-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.action-icon--spin {
  animation: topbar-spin 900ms linear infinite;
}

@keyframes topbar-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .top-bar {
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

  .search-pill {
    min-width: 180px;
  }
}
</style>
