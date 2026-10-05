<script setup lang="ts">
/** Read-only view of the signed-in administrator. */
import { computed } from 'vue'
import { ElCard, ElDescriptions, ElDescriptionsItem } from 'element-plus'

import DataStateView from '@/components/common/DataStateView.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { fetchCurrentUser } from '@/api/auth'
import { formatDateTime } from '@/utils/format'

const { data, loading, failed, error, reload } = useAsyncData(() => fetchCurrentUser())

const permissions = computed(() => data.value?.permissions ?? [])
</script>

<template>
  <ElCard shadow="never">
    <template #header>账号信息</template>

    <DataStateView
      :loading="loading"
      :failed="failed"
      :error="error"
      :empty="data === null"
      @retry="reload"
    >
      <ElDescriptions v-if="data" :column="2" border>
        <ElDescriptionsItem label="用户名">{{ data.user.username }}</ElDescriptionsItem>
        <ElDescriptionsItem label="显示名称">{{ data.user.display_name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="状态">
          <StatusTag :value="data.user.status" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="超级管理员">
          <StatusTag :value="data.is_super_admin" :boolean-labels="['否', '是']" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="邮箱">{{ data.user.email ?? '—' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="手机">{{ data.user.phone ?? '—' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="上次登录">
          {{ formatDateTime(data.user.last_login_at) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="创建时间">
          {{ formatDateTime(data.user.created_at) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="需要修改密码">
          <StatusTag :value="data.must_change_password" :boolean-labels="['否', '是']" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="密码已过期">
          <StatusTag :value="data.password_expired" :boolean-labels="['否', '是']" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="权限数量" :span="2">
          {{ permissions.length }}
        </ElDescriptionsItem>
      </ElDescriptions>
    </DataStateView>
  </ElCard>
</template>
