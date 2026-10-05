/** Blog administration (`app/blog/**`). */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  ApplicationQuery,
  Article,
  ArticleCreateRequest,
  ArticleQuery,
  ArticleReviewRequest,
  ArticleUpdateRequest,
  AuthorApplication,
  AuthorApplicationReviewRequest,
  AuthorQuery,
  BlogAuthor,
  BlogCategory,
  CategoryCreateRequest,
  CategoryQuery,
  CategoryUpdateRequest,
  Comment,
  CommentReviewRequest,
} from '@/types/blog'

// --- categories ------------------------------------------------------------

/** `GET /blog/categories` */
export function listCategories(query: CategoryQuery = {}): Promise<Page<BlogCategory>> {
  return get<Page<BlogCategory>>('/blog/categories', { params: query })
}

/** `POST /blog/categories` */
export function createCategory(payload: CategoryCreateRequest): Promise<BlogCategory> {
  return post<BlogCategory>('/blog/categories', payload, {
    vctn: { idempotencyKey: `create-blog-category:${payload.category_code}` },
  })
}

/** `PUT /blog/categories/{category_id}` */
export function updateCategory(
  categoryId: string,
  payload: CategoryUpdateRequest,
): Promise<BlogCategory> {
  return put<BlogCategory>(`/blog/categories/${categoryId}`, payload)
}

/** `DELETE /blog/categories/{category_id}` */
export function deleteCategory(categoryId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/blog/categories/${categoryId}`)
}

// --- articles --------------------------------------------------------------

/** `GET /blog/articles` */
export function listArticles(query: ArticleQuery = {}): Promise<Page<Article>> {
  return get<Page<Article>>('/blog/articles', { params: query })
}

/** `GET /blog/articles/review-queue` */
export function listReviewQueue(page = 1, pageSize = 20): Promise<Page<Article>> {
  return get<Page<Article>>('/blog/articles/review-queue', {
    params: { page, page_size: pageSize },
  })
}

/** `GET /blog/articles/{article_id}` */
export function getArticle(articleId: string): Promise<Article> {
  return get<Article>(`/blog/articles/${articleId}`)
}

/** `POST /blog/articles` */
export function createArticle(payload: ArticleCreateRequest): Promise<Article> {
  return post<Article>('/blog/articles', payload, {
    vctn: { idempotencyKey: `create-article:${payload.slug}` },
  })
}

/** `PUT /blog/articles/{article_id}` */
export function updateArticle(
  articleId: string,
  payload: ArticleUpdateRequest,
): Promise<Article> {
  return put<Article>(`/blog/articles/${articleId}`, payload)
}

/** `DELETE /blog/articles/{article_id}` */
export function deleteArticle(articleId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/blog/articles/${articleId}`)
}

/** `POST /blog/articles/{article_id}/publish` */
export function publishArticle(articleId: string): Promise<Article> {
  return post<Article>(`/blog/articles/${articleId}/publish`)
}

/** `POST /blog/articles/{article_id}/review` */
export function reviewArticle(
  articleId: string,
  payload: ArticleReviewRequest,
): Promise<Article> {
  return post<Article>(`/blog/articles/${articleId}/review`, payload)
}

/** `GET /blog/articles/{article_id}/tags` */
export function getArticleTags(articleId: string): Promise<string[]> {
  return get<string[]>(`/blog/articles/${articleId}/tags`)
}

// --- comments --------------------------------------------------------------

/** `GET /blog/articles/{article_id}/comments` */
export function listComments(
  articleId: string,
  page = 1,
  pageSize = 20,
): Promise<Page<Comment>> {
  return get<Page<Comment>>(`/blog/articles/${articleId}/comments`, {
    params: { page, page_size: pageSize },
  })
}

/** `GET /blog/comments/pending` */
export function listPendingComments(page = 1, pageSize = 20): Promise<Page<Comment>> {
  return get<Page<Comment>>('/blog/comments/pending', {
    params: { page, page_size: pageSize },
  })
}

/** `DELETE /blog/comments/{comment_id}` */
export function deleteComment(commentId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/blog/comments/${commentId}`)
}

/** `POST /blog/comments/{comment_id}/review` */
export function reviewComment(
  commentId: string,
  payload: CommentReviewRequest,
): Promise<Comment> {
  return post<Comment>(`/blog/comments/${commentId}/review`, payload)
}

// --- authors ---------------------------------------------------------------

/** `GET /blog/authors` */
export function listAuthors(query: AuthorQuery = {}): Promise<Page<BlogAuthor>> {
  return get<Page<BlogAuthor>>('/blog/authors', { params: query })
}

/** `GET /blog/authors/{author_id}` */
export function getAuthor(authorId: string): Promise<BlogAuthor> {
  return get<BlogAuthor>(`/blog/authors/${authorId}`)
}

/** `GET /blog/authors/applications` */
export function listAuthorApplications(
  query: ApplicationQuery = {},
): Promise<Page<AuthorApplication>> {
  return get<Page<AuthorApplication>>('/blog/authors/applications', { params: query })
}

/** `POST /blog/authors/applications/{application_id}/review` */
export function reviewAuthorApplication(
  applicationId: string,
  payload: AuthorApplicationReviewRequest,
): Promise<AuthorApplication> {
  return post<AuthorApplication>(
    `/blog/authors/applications/${applicationId}/review`,
    payload,
  )
}
