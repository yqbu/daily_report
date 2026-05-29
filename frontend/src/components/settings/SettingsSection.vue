<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  title: string
  description?: string
  icon: Component
}>()
</script>

<template>
  <section class="settings-section">
    <header class="settings-section-header">
      <div class="settings-section-title-row">
        <span class="settings-section-icon">
          <component :is="icon" />
        </span>
        <div class="settings-section-heading">
          <h2>{{ title }}</h2>
          <p v-if="description">{{ description }}</p>
        </div>
      </div>

      <div v-if="$slots.actions" class="settings-section-actions">
        <slot name="actions" />
      </div>
    </header>

    <div class="settings-section-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.settings-section {
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
  overflow: auto;
  scrollbar-gutter: stable;
}

.settings-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid #e6ebf3;
  background: #fbfcfe;
}

.settings-section-title-row {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.settings-section-icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  color: #2563eb;
  background: #eff6ff;
}

.settings-section-icon :deep(svg) {
  width: 17px;
  height: 17px;
}

.settings-section-heading {
  min-width: 0;
}

.settings-section-heading h2 {
  margin: 0;
  color: #172033;
  font-size: 15px;
  font-weight: 780;
  line-height: 1.25;
  letter-spacing: 0;
}

.settings-section-heading p {
  margin: 5px 0 0;
  color: #667085;
  font-size: 13px;
  line-height: 1.5;
}

.settings-section-body {
  flex: 1;
  display: grid;
  gap: 0;
  align-content: start;
}

.settings-section-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 760px) {
  .settings-section-header {
    align-items: stretch;
    flex-direction: column;
  }

  .settings-section-actions {
    justify-content: flex-start;
  }
}
</style>
