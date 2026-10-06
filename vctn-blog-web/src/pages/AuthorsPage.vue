<script setup lang="ts">
/** Author directory. */
import { listAuthors } from '@/api/blog'
import FeedState from '@/components/FeedState.vue'
import { useAsyncData } from '@/composables/use-async-data'

const authors = useAsyncData(async () => (await listAuthors(100)).items)
</script>

<template>
  <div class="authors-page">
    <h1 class="authors-page__title">作者</h1>

    <FeedState
      :loading="authors.loading.value"
      :failed="authors.failed.value"
      :error="authors.error.value"
      :empty="!authors.loading.value && (authors.data.value?.length ?? 0) === 0"
      empty-text="还没有作者"
      @retry="authors.reload()"
    >
      <div class="authors-page__grid">
        <RouterLink
          v-for="author in authors.data.value ?? []"
          :key="author.id"
          :to="{ name: 'author', params: { id: author.id } }"
          class="authors-page__card"
        >
          <ElAvatar :size="48">{{ author.author_name.slice(0, 1) }}</ElAvatar>
          <div class="authors-page__info">
            <span class="authors-page__name">{{ author.author_name }}</span>
            <span v-if="author.bio" class="authors-page__bio">{{ author.bio }}</span>
          </div>
        </RouterLink>
      </div>
    </FeedState>
  </div>
</template>

<style scoped>
.authors-page__title {
  margin: 0 0 var(--vctn-space-4);
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.authors-page__grid {
  display: grid;
  gap: var(--vctn-space-3);
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
}

.authors-page__card {
  display: flex;
  gap: var(--vctn-space-3);
  align-items: center;
  padding: var(--vctn-space-4);
  border: 1px solid var(--vctn-border);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
  text-decoration: none;
  box-shadow: var(--vctn-shadow-xs);
  transition:
    border-color var(--vctn-duration-base) var(--vctn-ease),
    box-shadow var(--vctn-duration-base) var(--vctn-ease);
}

.authors-page__card:hover {
  border-color: var(--vctn-border-brand);
  box-shadow: var(--vctn-shadow-md);
}

.authors-page__info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.authors-page__name {
  color: var(--vctn-text-strong);
  font-weight: 500;
}

.authors-page__bio {
  overflow: hidden;
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
