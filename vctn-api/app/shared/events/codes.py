"""Business event codes.

Codes are the contract between the module that raises an event and the growth /
points / task / achievement rules that consume it. Nothing outside this module
should spell a code literal.
"""

from __future__ import annotations

from typing import Final


class BehaviorEventCode:
    """Codes written into ``behavior_event.event_code``."""

    PAGE_VIEW: Final[str] = "PAGE_VIEW"
    PAGE_LEAVE: Final[str] = "PAGE_LEAVE"
    BUTTON_CLICK: Final[str] = "BUTTON_CLICK"
    TOOL_VIEW: Final[str] = "TOOL_VIEW"
    TOOL_START: Final[str] = "TOOL_START"
    TOOL_EXECUTE: Final[str] = "TOOL_EXECUTE"
    TOOL_EXECUTE_SUCCESS: Final[str] = "TOOL_EXECUTE_SUCCESS"
    TOOL_EXECUTE_FAILURE: Final[str] = "TOOL_EXECUTE_FAILURE"
    TOOL_COPY: Final[str] = "TOOL_COPY"
    TOOL_DOWNLOAD: Final[str] = "TOOL_DOWNLOAD"
    TOOL_CLEAR: Final[str] = "TOOL_CLEAR"
    USER_REGISTER: Final[str] = "USER_REGISTER"
    USER_LOGIN: Final[str] = "USER_LOGIN"
    USER_LOGOUT: Final[str] = "USER_LOGOUT"
    USER_SEARCH: Final[str] = "USER_SEARCH"
    USER_FAVORITE: Final[str] = "USER_FAVORITE"
    LEVEL_VIEW: Final[str] = "LEVEL_VIEW"
    POINT_VIEW: Final[str] = "POINT_VIEW"
    GROWTH_VIEW: Final[str] = "GROWTH_VIEW"
    ARTICLE_VIEW: Final[str] = "ARTICLE_VIEW"
    ARTICLE_LIKE: Final[str] = "ARTICLE_LIKE"
    ARTICLE_FAVORITE: Final[str] = "ARTICLE_FAVORITE"
    ARTICLE_COMMENT: Final[str] = "ARTICLE_COMMENT"
    AUTHOR_FOLLOW: Final[str] = "AUTHOR_FOLLOW"
    SEARCH: Final[str] = "SEARCH"
    SEARCH_RESULT_CLICK: Final[str] = "SEARCH_RESULT_CLICK"

    ALL: Final[frozenset[str]] = frozenset(
        {
            PAGE_VIEW,
            PAGE_LEAVE,
            BUTTON_CLICK,
            TOOL_VIEW,
            TOOL_START,
            TOOL_EXECUTE,
            TOOL_EXECUTE_SUCCESS,
            TOOL_EXECUTE_FAILURE,
            TOOL_COPY,
            TOOL_DOWNLOAD,
            TOOL_CLEAR,
            USER_REGISTER,
            USER_LOGIN,
            USER_LOGOUT,
            USER_SEARCH,
            USER_FAVORITE,
            LEVEL_VIEW,
            POINT_VIEW,
            GROWTH_VIEW,
            ARTICLE_VIEW,
            ARTICLE_LIKE,
            ARTICLE_FAVORITE,
            ARTICLE_COMMENT,
            AUTHOR_FOLLOW,
            SEARCH,
            SEARCH_RESULT_CLICK,
        }
    )


class GrowthEventCode:
    """Codes written into ``biz_growth_event.event_code``."""

    TOOL_EXECUTION_SUCCESS: Final[str] = "TOOL_EXECUTION_SUCCESS"
    BLOG_ARTICLE_PUBLISHED: Final[str] = "BLOG_ARTICLE_PUBLISHED"
    BLOG_COMMENT_CREATED: Final[str] = "BLOG_COMMENT_CREATED"
    BLOG_LIKE_RECEIVED: Final[str] = "BLOG_LIKE_RECEIVED"
    DAILY_LOGIN: Final[str] = "DAILY_LOGIN"
    USER_REGISTER: Final[str] = "USER_REGISTER"
    ACHIEVEMENT_UNLOCKED: Final[str] = "ACHIEVEMENT_UNLOCKED"
    TASK_COMPLETED: Final[str] = "TASK_COMPLETED"


class OutboxEventType:
    """Payload types carried through ``sys_outbox_event``."""

    BLOG_ARTICLE_PUBLISHED: Final[str] = "BLOG_ARTICLE_PUBLISHED"
    BLOG_COMMENT_CREATED: Final[str] = "BLOG_COMMENT_CREATED"
    BLOG_LIKE_RECEIVED: Final[str] = "BLOG_LIKE_RECEIVED"
    BLOG_AUTHOR_FOLLOWED: Final[str] = "BLOG_AUTHOR_FOLLOWED"
    TOOL_EXECUTED: Final[str] = "TOOL_EXECUTED"
    USER_REGISTERED: Final[str] = "USER_REGISTERED"
    USER_LOGGED_IN: Final[str] = "USER_LOGGED_IN"
    LEVEL_CHANGED: Final[str] = "LEVEL_CHANGED"
    ACHIEVEMENT_UNLOCKED: Final[str] = "ACHIEVEMENT_UNLOCKED"
    TASK_COMPLETED: Final[str] = "TASK_COMPLETED"


class JobType:
    """Types stored in ``sys_job.job_type``."""

    EXPORT: Final[str] = "EXPORT"
    LOG_PURGE: Final[str] = "LOG_PURGE"
    ANALYTICS_ROLLUP: Final[str] = "ANALYTICS_ROLLUP"
    TOOL_POPULARITY: Final[str] = "TOOL_POPULARITY"
    OUTBOX_DISPATCH: Final[str] = "OUTBOX_DISPATCH"
    NOTIFICATION_DISPATCH: Final[str] = "NOTIFICATION_DISPATCH"


class NotificationType:
    """Types stored in ``sys_notification.notification_type``."""

    SYSTEM: Final[str] = "SYSTEM"
    BLOG_REVIEW: Final[str] = "BLOG_REVIEW"
    AUTHOR_REVIEW: Final[str] = "AUTHOR_REVIEW"
    LEVEL_UP: Final[str] = "LEVEL_UP"
    ACHIEVEMENT: Final[str] = "ACHIEVEMENT"
    TASK_REWARD: Final[str] = "TASK_REWARD"
    EXPORT_READY: Final[str] = "EXPORT_READY"


class UserType:
    """``sys_notification.user_type`` discriminator."""

    ADMIN: Final[str] = "ADMIN"
    PLATFORM: Final[str] = "PLATFORM"
