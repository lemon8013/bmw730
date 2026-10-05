<script setup lang="ts">
/** Minimal shell used by the standalone pages (login, error screens). */
import { RouterView } from 'vue-router'
</script>

<template>
  <main class="blank-layout">
    <RouterView />
  </main>
</template>

<style scoped>
.blank-layout {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 24px;
}
</style>
