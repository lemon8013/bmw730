<script setup lang="ts">
/**
 * Header account area.
 *
 * Signed out it is a plain "登录 / 注册" link; signed in it is a dropdown with
 * the display name and a sign-out entry. The portal never blocks anonymous use,
 * so nothing here gates navigation.
 */
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

/** Keep the post-login destination attached to the link itself. */
const loginTarget = computed(() => ({
  name: 'login',
  query: { redirect: route.fullPath },
}))

const initial = computed(() => auth.displayName.slice(0, 1).toUpperCase())

async function signOut(): Promise<void> {
  await auth.signOut()
  ElMessage.success('已退出登录')
  void router.push({ name: 'home' })
}
</script>

<template>
  <div class="user-menu">
    <template v-if="auth.isAuthenticated">
      <ElDropdown trigger="click">
        <span class="user-menu__trigger">
          <ElAvatar class="user-menu__avatar" :size="26">{{ initial }}</ElAvatar>
          <span class="user-menu__name">{{ auth.displayName }}</span>
        </span>
        <template #dropdown>
          <ElDropdownMenu>
            <ElDropdownItem disabled>
              <span class="user-menu__identity">@{{ auth.username }}</span>
            </ElDropdownItem>
            <ElDropdownItem divided @click="signOut">退出登录</ElDropdownItem>
          </ElDropdownMenu>
        </template>
      </ElDropdown>
    </template>

    <template v-else>
      <RouterLink :to="loginTarget" class="user-menu__link">登录 / 注册</RouterLink>
    </template>
  </div>
</template>

<style scoped>
.user-menu {
  display: flex;
  align-items: center;
}

.user-menu__trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--vctn-space-2);
  height: 32px;
  padding: 0 var(--vctn-space-2);
  border: 1px solid transparent;
  border-radius: var(--vctn-radius-pill);
  cursor: pointer;
  outline: none;
  transition:
    background-color var(--vctn-duration-fast) var(--vctn-ease),
    border-color var(--vctn-duration-fast) var(--vctn-ease);
}

.user-menu__trigger:hover {
  border-color: var(--vctn-border);
  background-color: var(--vctn-bg-hover);
}

.user-menu__avatar {
  background: var(--vctn-brand);
  font-size: 13px;
}

.user-menu__name {
  max-width: 120px;
  overflow: hidden;
  font-size: var(--vctn-text-sm);
  font-weight: 500;
  color: var(--vctn-text-regular);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-menu__identity {
  font-size: var(--vctn-text-xs);
  color: var(--vctn-text-muted);
}

.user-menu__link {
  font-size: 13px;
  color: var(--vctn-text-regular);
  text-decoration: none;
  white-space: nowrap;
}

.user-menu__link:hover {
  color: var(--vctn-brand);
}
</style>
