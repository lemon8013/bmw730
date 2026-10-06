/**
 * Blog domain types.
 *
 * Mirrors the `app/blog` schema modules. Reading is anonymous — the list, detail,
 * category, author and comment endpoints all accept an optional principal —
 * while writing (posting, commenting, liking, authoring) needs a signed-in
 * business user.
 */

import type { EntityId, Page } from '@/types/api'

/** Lifecycle of an article. */
export type ArticleStatus = 'DRAFT' | 'PUBLISHED' | 'OFFLINE' | string

/** Review state of an article. */
export type ReviewStatus = 'NOT_REQUIRED' | 'PENDING' | 'APPROVED' | 'REJECTED' | string

/** A blog article. */
export interface Article {
  id: EntityId
  author_id: EntityId
  category_id: EntityId | null
  title: string
  slug: string
  summary: string | null
  cover_url: string | null
  content_markdown: string | null
  /** Server rendered HTML — preferred for display, no client parser needed. */
  content_html: string | null
  status: ArticleStatus
  review_status: ReviewStatus
  reviewer_id: EntityId | null
  reviewed_at: string | null
  published_at: string | null
  view_count: number
  like_count: number
  favorite_count: number
  comment_count: number
  tags: string[]
  created_at: string
  updated_at: string
}

/** Query accepted by `GET /blog/articles`. */
export interface ArticleQuery {
  keyword?: string
  category_id?: EntityId
  /** Filter by author. Required in practice for any non-published status. */
  author_id?: EntityId
  /**
   * Anything other than `PUBLISHED` is private to the author: the backend
   * narrows the result to the caller's own author row and rejects anonymous
   * callers with `401001`.
   */
  status?: ArticleStatus
  page?: number
  page_size?: number
}

/** Create a draft article. */
export interface ArticleCreateRequest {
  title: string
  slug: string
  summary?: string | null
  cover_url?: string | null
  category_id?: EntityId | null
  content_markdown?: string | null
  tags?: string[]
}

/** Update a draft article; every field is optional. */
export interface ArticleUpdateRequest {
  title?: string
  slug?: string
  summary?: string | null
  cover_url?: string | null
  category_id?: EntityId | null
  content_markdown?: string | null
  tags?: string[]
}

/** A blog category. */
export interface Category {
  id: EntityId
  category_code: string
  category_name: string
  description: string | null
  sort_order: number
  status: string
  created_at: string
  updated_at: string
}

/** A blog author. */
export interface Author {
  id: EntityId
  user_id: EntityId
  author_name: string
  bio: string | null
  avatar_url: string | null
  status: string
  approved_at: string | null
  created_at: string
  updated_at: string
}

/** Apply to become an author. */
export interface AuthorApplyRequest {
  author_name: string
  bio?: string | null
  avatar_url?: string | null
  application_reason?: string | null
}

/** A comment on an article. */
export interface Comment {
  id: EntityId
  article_id: EntityId | null
  user_id: EntityId | null
  parent_id: EntityId | null
  content: string
  status: string
  reviewer_id: EntityId | null
  created_at: string
  updated_at: string
}

/** Post a comment. */
export interface CommentCreateRequest {
  content: string
  parent_id?: EntityId | null
}

/** Like toggle result. */
export interface LikeResult {
  article_id: EntityId
  liked: boolean
  like_count: number
}

/** Favorite toggle result. */
export interface FavoriteResult {
  article_id: EntityId
  favorited: boolean
  favorite_count: number
}

/** Follow toggle result. */
export interface FollowResult {
  followed_user_id: EntityId
  following: boolean
}

/** A page of articles, matching the backend envelope. */
export type ArticlePage = Page<Article>
