<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'

import { useAppStore } from '../stores/app'

const app = useAppStore()
</script>

<template>
  <header class="top-bar">
    <div class="top-bar__brand">
      <span class="top-bar__logo">D</span>
      <span>Daily Reporter</span>
    </div>
    <div class="top-bar__actions">
      <el-date-picker
        v-model="app.currentDate"
        type="date"
        value-format="YYYY-MM-DD"
        :clearable="false"
        style="width: 150px"
      />
      <el-button class="glass-button" :icon="Refresh" @click="app.refreshCollectorStatus">
        刷新状态
      </el-button>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  display: flex;
  height: 64px;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.72);
  padding: 0 24px;
}

.top-bar__brand,
.top-bar__actions {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.top-bar__logo {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 11px;
  background: var(--app-primary);
  color: white;
  font-weight: 900;
}
</style>
