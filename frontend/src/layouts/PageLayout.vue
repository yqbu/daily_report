<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  scrollable?: boolean
}>()
</script>

<template>
  <article class="page-layout" :class="{ 'page-layout--scrollable': scrollable }">
    <header class="page-header">
      <div class="page-heading">
        <p class="page-kicker">功能界面</p>
        <h2 class="page-title">{{ title }}</h2>
        <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      </div>

      <div v-if="$slots.actions" class="page-actions">
        <slot name="actions" />
      </div>
    </header>

    <div class="page-body">
      <slot />
    </div>
  </article>
</template>

<style scoped>
.page-layout {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 24px 18px;
  border-bottom: 1px solid #e6ebf3;
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.74), rgba(255, 255, 255, 0.68)),
    #ffffff;
}

.page-heading {
  min-width: 0;
}

.page-kicker {
  margin: 0 0 7px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.page-title {
  margin: 0;
  color: #172033;
  font-size: 26px;
  font-weight: 740;
  line-height: 1.18;
  letter-spacing: 0;
}

.page-subtitle {
  max-width: 760px;
  margin: 8px 0 0;
  color: #667085;
  font-size: 14px;
  line-height: 1.65;
}

.page-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.page-body {
  min-height: 0;
  padding: 24px;
  overflow: hidden;
}

.page-layout--scrollable .page-body {
  overflow: auto;
  background: #ffffff;
  scrollbar-gutter: stable;
}

@media (max-width: 760px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
    padding: 18px;
  }

  .page-title {
    font-size: 22px;
  }

  .page-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .page-body {
    padding: 18px;
  }
}
</style>
