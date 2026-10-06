<script setup lang="ts">
/**
 * 等级：等级阶梯的增删改 + 按业务用户查看当前等级与升级历史。
 *
 * 此前这里是纯只读并提示「后端未提供写接口」。现已补齐 `/admin/levels` 写接口，
 * 与 `LEVEL_CONFIG_VIEW` / `LEVEL_CONFIG_EDIT` 权限对齐。
 *
 * 删除只能是软删：`biz_user_growth_account.current_level_id` 外键指向等级，
 * 一旦有用户达到过该等级，物理删除会被数据库拒绝。
 */
import { computed, reactive, ref } from 'vue'
import {
  ElButton,
  ElCard,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElTableColumn,
} from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import {
  createLevel,
  deleteLevel,
  getUserLevel,
  getUserLevelHistory,
  listAdminLevels,
  updateLevel,
} from '@/api/growth'
import BizUserPicker from '@/components/growth/BizUserPicker.vue'
import StatCard from '@/components/charts/StatCard.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import type { UserLevel } from '@/types/growth'
import { renderError } from '@/utils/error'
import { formatNumber } from '@/utils/format'

function failureText(caught: unknown): string {
  return renderError(caught).message
}

const notify = useConfirm()
const fields = useFieldPolicy(PERMISSION.levelConfigView)
const permission = usePermissionStore()

const canEdit = computed(() => permission.has(PERMISSION.levelConfigEdit))

const LEVEL_STATUS = ['ACTIVE', 'DISABLED'] as const
const STATUS_LABEL: Readonly<Record<string, string>> = {
  ACTIVE: '启用',
  DISABLED: '停用',
}

const MAX_PAGE_SIZE = 200

// ---------------------------------------------------------------------------
// 等级目录
// ---------------------------------------------------------------------------

const {
  data: levels,
  loading: levelsLoading,
  failed: levelsFailed,
  error: levelsError,
  reload: reloadLevels,
} = useAsyncData(() => listAdminLevels(true))

const levelRows = computed(
  () => (levels.value ?? []) as unknown as Record<string, unknown>[],
)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInstance>()

interface LevelForm {
  level_code: string
  level_name: string
  level_no: number
  min_growth_points: number
  max_growth_points: number | null
  icon_url: string
  description: string
  status: string
  sort_order: number
}

function emptyForm(): LevelForm {
  return {
    level_code: '',
    level_name: '',
    level_no: 1,
    min_growth_points: 0,
    max_growth_points: null,
    icon_url: '',
    description: '',
    status: 'ACTIVE',
    sort_order: 0,
  }
}

const form = reactive<LevelForm>(emptyForm())

const formRules: FormRules<LevelForm> = {
  level_code: [{ required: true, message: '请填写等级编码', trigger: 'blur' }],
  level_name: [{ required: true, message: '请填写等级名称', trigger: 'blur' }],
  level_no: [{ required: true, message: '请填写等级序号', trigger: 'change' }],
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const level = row as unknown as UserLevel
  editingId.value = level.id
  Object.assign(form, {
    level_code: level.level_code,
    level_name: level.level_name,
    level_no: level.level_no,
    min_growth_points: level.min_growth_points,
    max_growth_points: level.max_growth_points ?? null,
    icon_url: level.icon_url ?? '',
    description: level.description ?? '',
    status: level.status,
    sort_order: level.sort_order,
  })
  dialogVisible.value = true
}

async function submitLevel(): Promise<void> {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    if (editingId.value === null) {
      await createLevel({
        level_code: form.level_code,
        level_name: form.level_name,
        level_no: form.level_no,
        min_growth_points: form.min_growth_points,
        max_growth_points: form.max_growth_points,
        icon_url: form.icon_url || null,
        description: form.description || null,
        status: form.status,
        sort_order: form.sort_order,
      })
      notify.success('已新增等级')
    } else {
      await updateLevel(editingId.value, {
        level_name: form.level_name,
        level_no: form.level_no,
        min_growth_points: form.min_growth_points,
        max_growth_points: form.max_growth_points,
        icon_url: form.icon_url || null,
        description: form.description || null,
        status: form.status,
        sort_order: form.sort_order,
      })
      notify.success('已更新等级')
    }
    dialogVisible.value = false
    await reloadLevels()
  } catch (caught) {
    notify.failure(failureText(caught))
  } finally {
    submitting.value = false
  }
}

async function removeLevel(row: Record<string, unknown>): Promise<void> {
  const level = row as unknown as UserLevel
  const confirmed = await notify.confirm({
    title: '停用等级',
    message: `停用「${level.level_name}」后它将不再出现在等级阶梯中。已到达该等级的用户历史不受影响。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteLevel(level.id)
    notify.success('已停用等级')
    await reloadLevels()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 用户等级
// ---------------------------------------------------------------------------

const selectedUserId = ref('')
const historyPage = ref(1)
const historyPageSize = ref(20)

const {
  data: userLevel,
  loading: userLevelLoading,
  failed: userLevelFailed,
  error: userLevelError,
  reload: reloadUserLevel,
} = useAsyncData(() => getUserLevel(selectedUserId.value), { immediate: false })

const {
  data: history,
  loading: historyLoading,
  failed: historyFailed,
  error: historyError,
  reload: reloadHistory,
} = useAsyncData(
  () =>
    getUserLevelHistory(selectedUserId.value, {
      page: historyPage.value,
      page_size: historyPageSize.value,
    }),
  { immediate: false },
)

const historyRows = computed(
  () => (history.value?.items ?? []) as unknown as Record<string, unknown>[],
)

async function onUserChange(user: { user_id: string } | null): Promise<void> {
  const userId = user?.user_id ?? ''
  selectedUserId.value = userId
  if (!userId) {
    return
  }
  historyPage.value = 1
  await Promise.all([reloadUserLevel(), reloadHistory()])
}

function refreshAll(): void {
  void reloadLevels()
  if (selectedUserId.value) {
    void reloadUserLevel()
    void reloadHistory()
  }
}
</script>

<template>
  <div class="level-page">
    <PageHeader
      title="等级"
      description="等级阶梯的维护，以及按业务用户查看的当前等级与升级历史。"
    >
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="level-page__section">
      <template #header>
        <div class="level-page__header">
          <span>等级阶梯</span>
          <ElButton v-if="canEdit" type="primary" @click="openCreate">新增等级</ElButton>
        </div>
      </template>
      <BaseTable
        :rows="levelRows"
        :loading="levelsLoading"
        :failed="levelsFailed"
        :error="levelsError"
        :total="0"
        :page="1"
        :page-size="MAX_PAGE_SIZE"
        :paginated="false"
        row-key="level_code"
        empty-text="暂无等级"
        @retry="reloadLevels"
      >
        <ElTableColumn
          v-if="!fields.isHidden('level_code')"
          prop="level_code"
          label="等级编码"
          min-width="130"
        />
        <ElTableColumn
          v-if="!fields.isHidden('level_name')"
          prop="level_name"
          label="等级名称"
          min-width="140"
        />
        <ElTableColumn
          v-if="!fields.isHidden('level_no')"
          prop="level_no"
          label="序号"
          width="90"
        />
        <ElTableColumn label="成长值区间" min-width="170">
          <template #default="{ row }">
            {{ formatNumber(row.min_growth_points) }} ~
            {{ row.max_growth_points === null ? '∞' : formatNumber(row.max_growth_points) }}
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('sort_order')" prop="sort_order" label="排序" width="90" />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openEdit(row)">
              {{ canEdit ? '编辑' : '查看' }}
            </ElButton>
            <ElButton v-if="canEdit" link type="danger" @click="removeLevel(row)">停用</ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <ElCard shadow="never" class="level-page__section">
      <template #header>
        <div class="level-page__header">
          <span>用户等级</span>
          <BizUserPicker :model-value="selectedUserId" width="320px" @change="onUserChange" />
        </div>
      </template>

      <DataStateView
        :loading="userLevelLoading"
        :failed="userLevelFailed"
        :error="userLevelError"
        :empty="!selectedUserId || !userLevel"
        empty-text="请选择业务用户"
        @retry="reloadUserLevel"
      >
        <template v-if="userLevel">
          <div class="level-page__stats">
            <StatCard label="累计成长值" :value="formatNumber(userLevel.total_growth_points)" />
            <StatCard label="当前等级" :value="userLevel.current_level_name ?? '未达级'" />
            <StatCard label="下一等级" :value="userLevel.next_level_name ?? '已封顶'" />
            <StatCard label="等级变更次数" :value="formatNumber(userLevel.level_changed_count)" />
          </div>
        </template>
      </DataStateView>
    </ElCard>

    <ElCard v-if="selectedUserId" shadow="never" class="level-page__section">
      <template #header>升级历史</template>
      <BaseTable
        :rows="historyRows"
        :loading="historyLoading"
        :failed="historyFailed"
        :error="historyError"
        :total="history?.total ?? 0"
        :page="historyPage"
        :page-size="historyPageSize"
        :paginated="true"
        row-key="id"
        empty-text="暂无升级记录"
        @retry="reloadHistory"
        @update:page="(p: number) => { historyPage = p; void reloadHistory() }"
        @update:page-size="(s: number) => { historyPageSize = s; historyPage = 1; void reloadHistory() }"
      >
        <ElTableColumn label="从" min-width="130">
          <template #default="{ row }">{{ row.from_level_name ?? '—' }}</template>
        </ElTableColumn>
        <ElTableColumn label="到" min-width="130">
          <template #default="{ row }">{{ row.to_level_name ?? '—' }}</template>
        </ElTableColumn>
        <ElTableColumn prop="growth_points" label="当时成长值" width="130" />
        <ElTableColumn prop="reason" label="原因" min-width="180" show-overflow-tooltip />
        <ElTableColumn prop="created_at" label="时间" min-width="180" />
      </BaseTable>
    </ElCard>

    <ElDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增等级' : '编辑等级'"
      width="520px"
    >
      <ElForm ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <ElFormItem label="等级编码" prop="level_code">
          <ElInput v-model="form.level_code" :disabled="editingId !== null" placeholder="LV3" />
        </ElFormItem>
        <ElFormItem label="等级名称" prop="level_name">
          <ElInput v-model="form.level_name" />
        </ElFormItem>
        <ElFormItem label="等级序号" prop="level_no">
          <ElInputNumber v-model="form.level_no" :min="1" />
        </ElFormItem>
        <ElFormItem label="最小成长值">
          <ElInputNumber v-model="form.min_growth_points" :min="0" />
        </ElFormItem>
        <ElFormItem label="最大成长值">
          <ElInputNumber v-model="form.max_growth_points" :min="0" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="form.sort_order" :min="0" />
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="form.status">
            <ElOption
              v-for="value in LEVEL_STATUS"
              :key="value"
              :label="STATUS_LABEL[value] ?? value"
              :value="value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="图标地址">
          <ElInput v-model="form.icon_url" />
        </ElFormItem>
        <ElFormItem label="描述">
          <ElInput v-model="form.description" type="textarea" :rows="2" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitLevel">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.level-page__section {
  margin-top: 16px;
}

.level-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.level-page__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}
</style>
