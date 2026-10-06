/**
 * Blog API.
 *
 * Every read here is anonymous; the write calls need a signed-in business user
 * and fail with `401001` otherwise, which the pages turn into a "sign in to
 * continue" hint rather than a broken screen.
 */

import { httpClient } from '@/api/client'
import type { ApiEnvelope, EntityId, Page } from '@/types/api'
import type {
  Article,
  ArticleCreateRequest,
  ArticleQuery,
  ArticleUpdateRequest,
  Author,
  AuthorApplyRequest,
  Category,
  Comment,
  CommentCreateRequest,
  FavoriteResult,
  FollowResult,
  LikeResult,
} from '@/types/blog'

function unwrap<T>(envelope: ApiEnvelope<T>): T {
  return envelope.data as T
}

// ---------------------------------------------------------------- articles

/** Published article feed, optionally narrowed by keyword or category. */
export async function listArticles(query: ArticleQuery = {}): Promise<Page<Article>> {
  const response = await httpClient.get<ApiEnvelope<Page<Article>>>('/blog/articles', {
    params: {
      keyword: query.keyword || undefined,
      category_id: query.category_id || undefined,
      author_id: query.author_id || undefined,
      status: query.status || undefined,
      page: query.page ?? 1,
      page_size: query.page_size ?? 20,
    },
  })
  return unwrap(response.data)
}

/** One article. Only published articles are visible; each call counts a view. */
export async function getArticle(articleId: EntityId): Promise<Article> {
  const response = await httpClient.get<ApiEnvelope<Article>>(`/blog/articles/${articleId}`)
  return unwrap(response.data)
}

/** Tag names attached to an article. */
export async function getArticleTags(articleId: EntityId): Promise<string[]> {
  const response = await httpClient.get<ApiEnvelope<string[]>>(
    `/blog/articles/${articleId}/tags`,
  )
  return unwrap(response.data)
}

/** Create a draft article (requires a business user). */
export async function createArticle(payload: ArticleCreateRequest): Promise<Article> {
  const response = await httpClient.post<ApiEnvelope<Article>>('/blog/articles', payload)
  return unwrap(response.data)
}

/** Update one of the caller's own articles. */
export async function updateArticle(
  articleId: EntityId,
  payload: ArticleUpdateRequest,
): Promise<Article> {
  const response = await httpClient.put<ApiEnvelope<Article>>(
    `/blog/articles/${articleId}`,
    payload,
  )
  return unwrap(response.data)
}

/** Soft delete one of the caller's own articles. */
export async function deleteArticle(articleId: EntityId): Promise<void> {
  await httpClient.delete<ApiEnvelope<Record<string, never>>>(`/blog/articles/${articleId}`)
}

/** Submit a draft for publication. */
export async function publishArticle(articleId: EntityId): Promise<Article> {
  const response = await httpClient.post<ApiEnvelope<Article>>(
    `/blog/articles/${articleId}/publish`,
  )
  return unwrap(response.data)
}

// -------------------------------------------------------------- categories

/** Category directory. */
export async function listCategories(pageSize = 50): Promise<Page<Category>> {
  const response = await httpClient.get<ApiEnvelope<Page<Category>>>('/blog/categories', {
    params: { page: 1, page_size: pageSize },
  })
  return unwrap(response.data)
}

/** One category. */
export async function getCategory(categoryId: EntityId): Promise<Category> {
  const response = await httpClient.get<ApiEnvelope<Category>>(
    `/blog/categories/${categoryId}`,
  )
  return unwrap(response.data)
}

// ----------------------------------------------------------------- authors

/** Author directory. */
export async function listAuthors(pageSize = 50): Promise<Page<Author>> {
  const response = await httpClient.get<ApiEnvelope<Page<Author>>>('/blog/authors', {
    params: { page: 1, page_size: pageSize },
  })
  return unwrap(response.data)
}

/** One author. */
export async function getAuthor(authorId: EntityId): Promise<Author> {
  const response = await httpClient.get<ApiEnvelope<Author>>(`/blog/authors/${authorId}`)
  return unwrap(response.data)
}

/** Apply to become an author. */
export async function applyAuthor(payload: AuthorApplyRequest): Promise<Author> {
  const response = await httpClient.post<ApiEnvelope<Author>>('/blog/authors/apply', payload)
  return unwrap(response.data)
}

// ---------------------------------------------------------------- comments

/** Comments on an article. */
export async function listComments(
  articleId: EntityId,
  page = 1,
  pageSize = 20,
): Promise<Page<Comment>> {
  const response = await httpClient.get<ApiEnvelope<Page<Comment>>>(
    `/blog/articles/${articleId}/comments`,
    { params: { page, page_size: pageSize } },
  )
  return unwrap(response.data)
}

/** Post a comment (requires a business user). */
export async function createComment(
  articleId: EntityId,
  payload: CommentCreateRequest,
): Promise<Comment> {
  const response = await httpClient.post<ApiEnvelope<Comment>>(
    `/blog/articles/${articleId}/comments`,
    payload,
  )
  return unwrap(response.data)
}

// ------------------------------------------------------------- interactions

/**
 * Set the like state of an article.
 *
 * The backend models this as a pair — `POST` to create, `DELETE` to remove — so
 * the desired end state is passed in rather than blindly toggling, which would
 * drift out of sync after a failed request.
 */
export async function setArticleLike(
  articleId: EntityId,
  liked: boolean,
): Promise<LikeResult> {
  const url = `/blog/articles/${articleId}/like`
  const response = liked
    ? await httpClient.post<ApiEnvelope<LikeResult>>(url)
    : await httpClient.delete<ApiEnvelope<LikeResult>>(url)
  return unwrap(response.data)
}

/** Set the favorite state of an article. */
export async function setArticleFavorite(
  articleId: EntityId,
  favorited: boolean,
): Promise<FavoriteResult> {
  const url = `/blog/articles/${articleId}/favorite`
  const response = favorited
    ? await httpClient.post<ApiEnvelope<FavoriteResult>>(url)
    : await httpClient.delete<ApiEnvelope<FavoriteResult>>(url)
  return unwrap(response.data)
}

/** Set the follow state for another user. */
export async function setUserFollow(
  userId: EntityId,
  following: boolean,
): Promise<FollowResult> {
  const url = `/blog/users/${userId}/follow`
  const response = following
    ? await httpClient.post<ApiEnvelope<FollowResult>>(url)
    : await httpClient.delete<ApiEnvelope<FollowResult>>(url)
  return unwrap(response.data)
}
