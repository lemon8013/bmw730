<script setup lang="ts">
/** 工具分类：只读展示后端公开分类目录。 */
import { computed } from 'vue'
import { ElAlert, ElButton, ElCard, ElTableColumn } from 'element-plus'

import { listCategories } from '@/api/catalog'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.toolCategoryView)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

const { data, loading, failed, error, reload } = useAsyncData(() => listCategories())

const rows = computed(() => asRows(data.value ?? []))
</script>

<template>
  <div class="tool-category-page">
    <PageHeader title="工具分类" description="展示工具的分类目录，用于工具归类与展示排序。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="warning"
      :closable="false"
      show-icon
      class="tool-category-page__notice"
      title="本页为只读"
      description="后端未提供工具分类的管理端增删改接口（/admin/tool-categories 尚未实现），分类数据来自公开目录 /tool-categories，因此本页不支持新增、编辑或删除。"
    />

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="rows.length"
        :page="1"
        :page-size="rows.length || 1"
        :paginated="false"
        empty-text="暂无工具分类"
        @retry="reload"
      >
        <ElTableColumn
          v-if="!fields.isHidden('category_code')"
          prop="category_code"
          label="分类编码"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('category_name')"
          prop="category_name"
          label="分类名称"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('description')"
          prop="description"
          label="描述"
          min-width="240"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('icon_url')"
          prop="icon_url"
          label="图标地址"
          min-width="200"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('sort_order')"
          prop="sort_order"
          label="排序"
          width="90"
        />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>
  </div>
</template>

<style scoped>
.tool-category-page__notice {
  margin-bottom: 16px;
}
</style>
