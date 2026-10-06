<script setup lang="ts">
/** Locally recorded recent usage (server side recents need a signed-in user). */
import { computed } from 'vue'
import { ElButton, ElCard } from 'element-plus'

import { listTools } from '@/api/tools'
import AppBreadcrumb from '@/components/AppBreadcrumb.vue'
import AsyncSection from '@/components/AsyncSection.vue'
import ToolCard from '@/components/ToolCard.vue'
import { clearRecentSlugs, readRecentSlugs } from '@/composables/recent-tools'
import { useAsyncData } from '@/composables/use-async-data'
import type { ToolCatalogItem } from '@/types/catalog'

const state = useAsyncData<ToolCatalogItem[]>(() => listTools())

const recentTools = computed<ToolCatalogItem[]>(() => {
  const bySlug = new Map((state.data.value ?? []).map((tool) => [tool.slug, tool]))
  return readRecentSlugs()
    .map((slug) => bySlug.get(slug))
    .filter((tool): tool is ToolCatalogItem => tool !== undefined)
})

function clearAll(): void {
  clearRecentSlugs()
  state.reload()
}
</script>

<template>
  <div class="recent-page">
    <AppBreadcrumb :entries="[{ label: '最近使用' }]" />

    <ElCard shadow="never" class="recent-page__head">
      <div class="recent-page__head-inner">
        <div>
          <h1 class="recent-page__title">最近使用</h1>
          <p class="recent-page__desc">
            记录保存在本机浏览器中，只存工具标识，不含任何输入输出内容。
          </p>
        </div>
        <ElButton v-if="recentTools.length > 0" @click="clearAll">清空记录</ElButton>
      </div>
    </ElCard>

    <ElCard shadow="never">
      <ElAlert
        type="info"
        :closable="false"
        show-icon
        class="recent-page__notice"
        title="登录后的跨设备使用记录暂未开放"
        description="服务端“最近使用”需要业务用户登录（tools-web 登录尚未实现），当前先提供本机记录。"
      />
      <AsyncSection
        :loading="state.loading.value"
        :failed="state.failed.value"
        :error="state.error.value"
        :empty="recentTools.length === 0"
        empty-text="还没有使用记录，去首页挑个工具试试"
        @retry="state.reload"
      >
        <div class="recent-page__grid">
          <ToolCard v-for="tool in recentTools" :key="tool.id" :tool="tool" />
        </div>
      </AsyncSection>
    </ElCard>
  </div>
</template>

<style scoped>
.recent-page__head {
  margin-bottom: 16px;
}

.recent-page__head-inner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.recent-page__title {
  margin: 0 0 6px;
  font-size: 18px;
}

.recent-page__desc {
  margin: 0;
  color: var(--vctn-text-secondary);
  font-size: 13px;
}

.recent-page__notice {
  margin-bottom: 16px;
}

.recent-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
</style>
