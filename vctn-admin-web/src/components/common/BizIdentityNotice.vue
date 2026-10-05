<script setup lang="ts">
/**
 * Explains why a page has no per-account data to show.
 *
 * The `/growth/me`, `/points/me`, `/tasks/me` and `/cosmetics/me` family of
 * endpoints all resolve identity from a **platform business user**, not from an
 * operator session. The admin console signs in as a `sys_user`, so the server
 * answers 401 `401001 "a business user identity is required"`.
 *
 * Rather than surfacing that as a load failure, pages that depend on those
 * endpoints render this notice so the page stays readable.
 */
import { ElAlert } from 'element-plus'

withDefaults(
  defineProps<{
    /** What would normally appear in place of this notice. */
    subject?: string
  }>(),
  {
    subject: '该数据',
  },
)
</script>

<template>
  <ElAlert type="warning" :closable="false" show-icon class="biz-identity-notice">
    <template #title>{{ subject }}需要平台业务用户身份</template>
    <p class="biz-identity-notice__desc">
      成长值、积分、任务与已获得装扮都挂在<b>平台业务用户</b>名下，后端现有端点只提供
      <code>/me</code> 形式（按当前登录的业务用户取数）。管理平台以<b>管理员身份</b>
      登录，不具备业务身份，因此服务端返回 401 而无法取数。
    </p>
    <p class="biz-identity-notice__desc">
      本页因此不展示个人账户数据。若要让管理员查看指定用户的成长数据，需要后端先冻结
      <code>/api/v1/admin/users/{user_id}/growth</code> 一类按用户查询的管理端点。
    </p>
  </ElAlert>
</template>

<style scoped>
.biz-identity-notice__desc {
  margin: 6px 0 0;
  line-height: 1.7;
}

.biz-identity-notice code {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--el-fill-color-dark);
  font-size: 12px;
}
</style>
