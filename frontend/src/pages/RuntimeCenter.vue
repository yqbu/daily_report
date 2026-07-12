<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import { Delete, Refresh, SwitchButton, Tools, VideoPlay } from '@element-plus/icons-vue'

import RuntimeLoadingOverlay from '../components/runtime/RuntimeLoadingOverlay.vue'
import RuntimeCenter from '../components/settings/RuntimeCenter.vue'
import type { RuntimeSummary } from '../api/runtimeCenter'

interface RuntimeCenterHandle {
  refreshSummary: () => Promise<void>
  startCollectorAction: () => Promise<void>
  stopCollectorAction: () => Promise<void>
  restartCollectorAction: () => Promise<void>
  handleDoctor: () => Promise<void>
  handleRepair: () => Promise<void>
  handleCleanupPreview: () => Promise<void>
  handleCleanupExecute: () => Promise<void>
}

const runtimeCenter = ref<RuntimeCenterHandle | null>(null)
const runtimeSummary = shallowRef<RuntimeSummary | null>(null)
const activeAction = shallowRef<string | null>(null)
const cleanupPreviewCount = shallowRef(0)
const pageLoading = shallowRef(false)
const loadingText = shallowRef('正在刷新运行状态…')

const collectorRunning = computed(() => runtimeSummary.value?.collector_status === 'running')
const isBusy = computed(() => Boolean(activeAction.value))

async function callRuntimeAction(name: string, action: keyof RuntimeCenterHandle): Promise<void> {
  if (activeAction.value) return
  activeAction.value = name
  try {
    await runtimeCenter.value?.[action]()
  } finally {
    activeAction.value = null
  }
}

function handleRefreshed(summary: RuntimeSummary): void {
  runtimeSummary.value = summary
}

function handleBusy(name: string | null): void {
  activeAction.value = name
}

function handleLoading(active: boolean, text: string): void {
  pageLoading.value = active
  if (text) loadingText.value = text
}
</script>

<template>
  <div class="runtime-page">
    <header class="runtime-page-topbar">
      <div class="title-block">
        <span class="workspace-label">Daily Report</span>
        <h1 class="page-title">运行中心</h1>
      </div>

      <div class="top-actions">
        <button
          class="top-button"
          type="button"
          :disabled="isBusy"
          title="刷新运行状态"
          @click="callRuntimeAction('refresh', 'refreshSummary')"
        >
          <Refresh class="action-icon" :class="{ 'action-icon--spin': activeAction === 'refresh' }" />
          <span>刷新</span>
        </button>

        <button
          class="top-button top-button--primary"
          type="button"
          :disabled="isBusy || collectorRunning"
          title="启动采集器"
          @click="callRuntimeAction('start', 'startCollectorAction')"
        >
          <VideoPlay class="action-icon" />
          <span>{{ collectorRunning ? '采集器运行中' : '启动采集器' }}</span>
        </button>

        <button
          class="top-button"
          type="button"
          :disabled="isBusy || !collectorRunning"
          title="停止采集器"
          @click="callRuntimeAction('stop', 'stopCollectorAction')"
        >
          <SwitchButton class="action-icon" />
          <span>停止</span>
        </button>

        <button
          class="top-button"
          type="button"
          :disabled="isBusy"
          title="重启采集器"
          @click="callRuntimeAction('restart', 'restartCollectorAction')"
        >
          <Refresh class="action-icon" :class="{ 'action-icon--spin': activeAction === 'restart' }" />
          <span>重启</span>
        </button>

        <button
          class="top-button"
          type="button"
          :disabled="isBusy"
          title="运行诊断"
          @click="callRuntimeAction('doctor', 'handleDoctor')"
        >
          <Tools class="action-icon" />
          <span>诊断</span>
        </button>

        <button
          class="top-button"
          type="button"
          :disabled="isBusy"
          title="修复过期运行状态，不会终止进程"
          @click="callRuntimeAction('repair', 'handleRepair')"
        >
          <Tools class="action-icon" />
          <span>安全修复</span>
        </button>

        <button
          class="top-button"
          type="button"
          :disabled="isBusy"
          title="预览可清理的孤儿进程"
          @click="callRuntimeAction('cleanup-preview', 'handleCleanupPreview')"
        >
          <Delete class="action-icon" />
          <span>预览清理</span>
        </button>

        <button
          class="top-button top-button--warning"
          type="button"
          :disabled="isBusy || cleanupPreviewCount === 0"
          title="执行预览列表中的孤儿进程清理"
          @click="callRuntimeAction('cleanup-execute', 'handleCleanupExecute')"
        >
          <Delete class="action-icon" />
          <span>执行清理</span>
        </button>
      </div>
    </header>

    <section class="runtime-page-body">
      <div class="runtime-page-scroll">
        <RuntimeCenter
          ref="runtimeCenter"
          @refreshed="handleRefreshed"
          @busy="handleBusy"
          @loading="handleLoading"
          @cleanup-preview-changed="cleanupPreviewCount = $event"
        />
      </div>
      <RuntimeLoadingOverlay :visible="pageLoading" :text="loadingText" />
    </section>
  </div>
</template>

<style scoped>
.runtime-page {
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

.runtime-page-topbar {
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
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.top-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #526179;
  background: #fff;
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
}

.top-button:hover {
  color: #409eff;
  border-color: #c9dcff;
  background: #eff6ff;
}

.top-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.top-button--primary {
  color: #fff;
  border-color: #2563eb;
  background: #2563eb;
}

.top-button--primary:hover {
  color: #fff;
  border-color: #1d4ed8;
  background: #1d4ed8;
}

.top-button--warning {
  color: #8a5a00;
  border-color: #f4d690;
  background: #fff8e5;
}

.top-button--warning:hover {
  color: #7a4d00;
  border-color: #e6a23c;
  background: #fff3d0;
}

.action-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.action-icon--spin {
  animation: runtime-spin 900ms linear infinite;
}

.runtime-page-body {
  position: relative;
  isolation: isolate;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
}

.runtime-page-scroll {
  width: 100%;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
}

.runtime-page-scroll :deep(.runtime-center) {
  min-height: 100%;
  height: auto;
}

@keyframes runtime-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 980px) {
  .runtime-page-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .top-actions {
    justify-content: flex-start;
  }
}
</style>
