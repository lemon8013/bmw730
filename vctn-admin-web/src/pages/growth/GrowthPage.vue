<script setup lang="ts">
/**
 * Growth value.
 *
 * The only growth endpoints the backend exposes today are `/growth/me` and
 * `/growth/me/transactions`, both of which resolve identity from the signed-in
 * **business user**. The console signs in as an operator, so instead of
 * rendering a load failure this page states the constraint and points at the
 * catalogue pages that do work.
 */
import { ElCard, ElSpace } from 'element-plus'

import BizIdentityNotice from '@/components/common/BizIdentityNotice.vue'
import PageHeader from '@/components/common/PageHeader.vue'
</script>

<template>
  <div class="growth-page">
    <PageHeader title="成长值" description="成长值账户与流水（按业务用户取数）。" />

    <BizIdentityNotice subject="成长值账户与流水" />

    <ElCard shadow="never" class="growth-page__related">
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
.growth-page__related {
  margin-top: 16px;
}
</style>
