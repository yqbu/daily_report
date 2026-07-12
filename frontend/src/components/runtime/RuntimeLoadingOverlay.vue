<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'

defineProps<{
  visible: boolean
  text: string
}>()
</script>

<template>
  <div v-if="visible" class="runtime-loading-overlay" role="status" aria-live="polite">
    <span class="runtime-loading-progress" />
    <div class="runtime-loading-indicator">
      <Loading class="runtime-loading-spinner" />
      <span>{{ text }}</span>
    </div>
  </div>
</template>

<style scoped>
.runtime-loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  color: #2563eb;
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(1px);
  pointer-events: auto;
}

.runtime-loading-progress {
  position: absolute;
  top: 0;
  left: 0;
  width: 38%;
  height: 3px;
  border-radius: 999px;
  background: #2563eb;
  box-shadow: 0 0 12px rgba(37, 99, 235, 0.35);
  animation: runtime-progress 1.1s ease-in-out infinite;
}

.runtime-loading-indicator {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid #d8e5ff;
  border-radius: 8px;
  color: #344054;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12);
  font-size: 13px;
  font-weight: 650;
}

.runtime-loading-spinner {
  width: 22px;
  height: 22px;
  color: #2563eb;
  animation: runtime-spin 850ms linear infinite;
}

@keyframes runtime-progress {
  0% {
    transform: translateX(-105%);
  }

  100% {
    transform: translateX(365%);
  }
}

@keyframes runtime-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
