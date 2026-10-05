/**
 * Blog payloads, matching the schemas under `app/blog`.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

/** `CategoryResponse`. */
export interface BlogCategory {
  id: EntityId
  category_code: string
  category_name: string
  description?: string | null
  sort_order: number
  status: string
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `CategoryCreateRequest`. */
export interface CategoryCreateRequest {
  category_code: string
  category_name: string
  description?: string | null
  sort_order?: number
}

/** `CategoryUpdateRequest`. */
export interface CategoryUpdateRequest {
  category_name?: string | null
  description?: string | null
  sort_order?: number | null
  status?: string | null
}

/** `ArticleResponse`. */
export interface Article {
  id: EntityId
  author_id: EntityId
  category_id?: EntityId | null
  title: string
  slug: string
  summary?: string | null
  cover_url?: string | null
  content_markdown?: string | null
  content_html?: string | null
  status: string
  review_status: string
  reviewer_id?: EntityId | null
  reviewed_at?: IsoDateTime | null
  published_at?: IsoDateTime | null
  view_count: number
  like_count: number
  favorite_count: number
  comment_count: number
  tags?: string[]
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `ArticleCreateRequest`. */
export interface ArticleCreateRequest {
  title: string
  slug: string
  summary?: string | null
  cover_url?: string | null
  category_id?: EntityId | null
  content_markdown?: string | null
  tags?: string[]
}

/** `ArticleUpdateRequest`. */
export interface ArticleUpdateRequest {
  title?: string | null
  slug?: string | null
  summary?: string | null
  cover_url?: string | null
  category_id?: EntityId | null
  content_markdown?: string | null
  tags?: string[] | null
}

/** `ArticleReviewRequest`. */
export interface ArticleReviewRequest {
  decision: string
  review_comment?: string | null
}

/** `CommentResponse`. */
export interface Comment {
  id: EntityId
  article_id?: EntityId | null
  user_id?: EntityId | null
  parent_id?: EntityId | null
  content: string
  status: string
  reviewer_id?: EntityId | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `CommentReviewRequest`. */
export interface CommentReviewRequest {
  decision: string
  review_comment?: string | null
}

/** `AuthorResponse`. */
export interface BlogAuthor {
  id: EntityId
  user_id: EntityId
  author_name: string
  bio?: string | null
  avatar_url?: string | null
  status: string
  approved_at?: IsoDateTime | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `AuthorApplicationResponse`. */
export interface AuthorApplication {
  id: EntityId
  user_id: EntityId
  application_reason?: string | null
  status: string
  review_reason?: string | null
  applied_at: IsoDateTime
  reviewed_at?: IsoDateTime | null
}

/** `AuthorApplicationReviewRequest`. */
export interface AuthorApplicationReviewRequest {
  decision: string
  review_reason?: string | null
}

/** Query parameters of `GET /blog/articles`. */
export interface ArticleQuery {
  keyword?: string
  category_id?: EntityId
  status?: string
  page?: number
  page_size?: number
}

/** Query parameters of `GET /blog/authors`. */
export interface AuthorQuery {
  status?: string
  page?: number
  page_size?: number
}

/** Query parameters of `GET /blog/authors/applications`. */
export interface ApplicationQuery {
  status?: string
  page?: number
  page_size?: number
}

/** Query parameters of `GET /blog/categories`. */
export interface CategoryQuery {
  keyword?: string
  status?: string
  page?: number
  page_size?: number
}
