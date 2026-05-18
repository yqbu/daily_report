<template>
  <div class="app-shell flex">
    <Sidebar />
    <div class="main-area flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <main ref="contentRef" class="page-host min-h-0 min-w-0 flex-1 overflow-hidden">
        <RouterView v-slot="{ Component }">
          <component :is="Component" />
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Sidebar from '../components/Sidebar.vue'

const route = useRoute()
const contentRef = ref<HTMLElement | null>(null)

watch(
  () => route.fullPath,
  () => {
    if (contentRef.value) contentRef.value.scrollTop = 0
  }
)
</script>

<style scoped>
.main-area {
  background: var(--app-bg);
}

.page-host {
  background: var(--app-bg);
  padding: 24px;
}
</style>
