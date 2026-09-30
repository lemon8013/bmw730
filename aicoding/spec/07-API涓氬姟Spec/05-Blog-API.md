# 05 Blog API

## Public/User

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /blog/categories | Public | 分类 |
| GET | /blog/articles | Public | 只返回公开发布文章 |
| GET | /blog/articles/{id} | Public | 查询文章并记录 ARTICLE_VIEW |
| GET | /blog/articles/{id}/comments | Public | 查询已发布评论 |
| POST | /blog/articles/{id}/like | Auth | 幂等点赞 |
| DELETE | /blog/articles/{id}/like | Auth | 取消点赞 |
| POST | /blog/articles/{id}/favorite | Auth | 幂等收藏 |
| DELETE | /blog/articles/{id}/favorite | Auth | 取消收藏 |
| POST | /blog/articles/{id}/comments | Auth | 创建评论，风控/敏感策略后写入 |
| DELETE | /blog/comments/{id} | Auth | 仅作者本人或管理员按权限删除 |
| POST | /blog/users/{id}/follow | Auth | 关注 |
| DELETE | /blog/users/{id}/follow | Auth | 取消关注 |
| GET | /blog/users/{id} | Public | 用户/作者公开资料 |

## Author

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| POST | /blog/author/applications | Auth | 创建作者申请，防重复 |
| GET | /blog/author/application | Auth | 查看自己的申请 |
| GET | /blog/author/me | Auth | 作者状态 |
| GET | /blog/author/articles | Auth | 自己的文章 |
| POST | /blog/author/articles | Auth(Author) | 创建草稿 |
| GET | /blog/author/articles/{id} | Auth(Author) | 仅自己可编辑 |
| PUT | /blog/author/articles/{id} | Auth(Author) | 更新草稿 |
| DELETE | /blog/author/articles/{id} | Auth(Author) | 删除草稿 |
| POST | /blog/author/articles/{id}/submit-review | Auth(Author) | DRAFT → REVIEW |
| POST | /blog/author/articles/{id}/publish | Auth(Author) | 仅按冻结审核/发布规则执行；未冻结则 BLOCKER |

## Admin Blog

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /admin/blog/author-applications | BLOG_AUTHOR_REVIEW | 查询申请 |
| GET | /admin/blog/author-applications/{id} | BLOG_AUTHOR_REVIEW | 详情 |
| POST | /admin/blog/author-applications/{id}/approve | BLOG_AUTHOR_REVIEW | 审核通过，创建/激活 blog_author |
| POST | /admin/blog/author-applications/{id}/reject | BLOG_AUTHOR_REVIEW | 拒绝并记录原因 |
| GET | /admin/blog/articles | BLOG_ARTICLE_REVIEW | 管理文章 |
| POST | /admin/blog/articles/{id}/approve | BLOG_ARTICLE_REVIEW | 审核通过 |
| POST | /admin/blog/articles/{id}/reject | BLOG_ARTICLE_REVIEW | 驳回 |
| POST | /admin/blog/articles/{id}/publish | BLOG_ARTICLE_PUBLISH | 发布 |
