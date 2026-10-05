<script setup lang="ts">
/**
 * Tasks.
 *
 * Both `/tasks` and `/tasks/me` resolve identity from the signed-in **business
 * user**, so an operator session gets 401. Instead of failing to load, the page
 * states the constraint and links to neighbouring pages that do work.
 */
import { ElCard, ElSpace } from 'element-plus'

import BizIdentityNotice from '@/components/common/BizIdentityNotice.vue'
import PageHeader from '@/components/common/PageHeader.vue'
</script>

<template>
  <div class="task-page">
    <PageHeader title="任务" description="任务目录与任务进度（按业务用户取数）。" />

    <BizIdentityNotice subject="任务目录与任务进度" />

    <ElCard shadow="never" class="task-page__related">
      <template #header>可用页面</template>
      <ElSpace wrap>
        <RouterLink to="/growth/levels">等级</RouterLink>
        <RouterLink to="/growth/achievements">成就</RouterLink>
        <RouterLink to="/growth/cosmetics">装扮</RouterLink>
      </ElSpace>
    </ElCard>
  </div>
</template>

<style scoped>
.task-page__related {
  margin-top: 16px;
}
</style>
