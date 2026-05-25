<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Calendar, Connection, Search } from '@element-plus/icons-vue'

const route = useRoute()

const pageTitle = computed(() => String(route.meta.title || 'Daily Report'))
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

    <div class="top-actions">
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

.search-pill,
.info-pill {
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
