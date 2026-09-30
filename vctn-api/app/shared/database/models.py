"""Import every ORM model so ``Base.metadata`` is fully populated.

Alembic uses ``Base.metadata`` as ``target_metadata``; importing this module
guarantees no table is missed.
"""

from __future__ import annotations

from app.admin.audit.model import (
    SysAccessLog,
    SysApplicationLog,
    SysAuditLog,
    SysOperationLog,
    SysSecurityLog,
)
from app.admin.auth.model import SysMfaFactor, SysPasswordHistory, SysSession
from app.admin.config.model import SysConfig, SysFeatureFlag
from app.admin.departments.model import SysDepartment
from app.admin.dictionaries.model import SysDictItem, SysDictType
from app.admin.permissions.model import SysPermission, SysPermissionField, SysRolePermission
from app.admin.roles.model import SysRole, SysRoleDataScope, SysRoleInheritance, SysUserRole
from app.admin.users.model import SysUser
from app.analytics.events.model import BehaviorEvent, BehaviorIdentityMerge
from app.analytics.statistics.model import (
    BehaviorEventDaily,
    BehaviorFunnel,
    BehaviorPageDaily,
    BehaviorSearchDaily,
    BehaviorToolDaily,
    BehaviorUserDaily,
)
from app.blog.articles.model import BlogArticle, BlogArticleTag
from app.blog.authors.model import BlogAuthor, BlogAuthorApplication
from app.blog.categories.model import BlogCategory
from app.blog.comments.model import BlogComment
from app.blog.interactions.model import BlogArticleFavorite, BlogArticleLike, BlogUserFollow
from app.platform.cosmetics.model import BizCosmetic, BizUserCosmetic, BizUserEquipment
from app.platform.growth.model import (
    BizAchievement,
    BizGrowthEvent,
    BizGrowthRule,
    BizTask,
    BizUserAchievement,
    BizUserGrowthAccount,
    BizUserGrowthTransaction,
    BizUserTask,
)
from app.platform.levels.model import BizUserLevel, BizUserLevelBenefit, BizUserLevelHistory
from app.platform.notifications.model import SysNotification
from app.platform.points.model import BizPointRule, BizPointTransaction, BizUserPointAccount
from app.platform.users.model import (
    BizUser,
    BizUserLoginIdentity,
    BizUserLoginLog,
    BizUserPasswordHistory,
    BizUserProfile,
    BizUserSession,
    BizUserVerification,
)
from app.system.files.model import SysExportJob, SysFile
from app.system.jobs.model import SysIdempotencyRecord, SysJob, SysJobDefinition, SysOutboxEvent
from app.system.risk.model import RiskRule
from app.tools.access.model import ToolAccessPolicy
from app.tools.catalog.model import Tool, ToolCategory, ToolComponentRegistry, ToolVersion
from app.tools.statistics.model import ToolPopularityDaily, ToolUsageDaily
from app.tools.usage.model import ToolRecentUsage, ToolUsageEvent

__all__ = [
    "BehaviorEvent",
    "BehaviorEventDaily",
    "BehaviorFunnel",
    "BehaviorIdentityMerge",
    "BehaviorPageDaily",
    "BehaviorSearchDaily",
    "BehaviorToolDaily",
    "BehaviorUserDaily",
    "BizAchievement",
    "BizCosmetic",
    "BizGrowthEvent",
    "BizGrowthRule",
    "BizPointRule",
    "BizPointTransaction",
    "BizTask",
    "BizUser",
    "BizUserAchievement",
    "BizUserCosmetic",
    "BizUserEquipment",
    "BizUserGrowthAccount",
    "BizUserGrowthTransaction",
    "BizUserLevel",
    "BizUserLevelBenefit",
    "BizUserLevelHistory",
    "BizUserLoginIdentity",
    "BizUserLoginLog",
    "BizUserPasswordHistory",
    "BizUserPointAccount",
    "BizUserProfile",
    "BizUserSession",
    "BizUserTask",
    "BizUserVerification",
    "BlogArticle",
    "BlogArticleFavorite",
    "BlogArticleLike",
    "BlogArticleTag",
    "BlogAuthor",
    "BlogAuthorApplication",
    "BlogCategory",
    "BlogComment",
    "BlogUserFollow",
    "RiskRule",
    "SysAccessLog",
    "SysApplicationLog",
    "SysAuditLog",
    "SysConfig",
    "SysDepartment",
    "SysDictItem",
    "SysDictType",
    "SysExportJob",
    "SysFeatureFlag",
    "SysFile",
    "SysIdempotencyRecord",
    "SysJob",
    "SysJobDefinition",
    "SysMfaFactor",
    "SysNotification",
    "SysOperationLog",
    "SysOutboxEvent",
    "SysPasswordHistory",
    "SysPermission",
    "SysPermissionField",
    "SysRole",
    "SysRoleDataScope",
    "SysRoleInheritance",
    "SysRolePermission",
    "SysSecurityLog",
    "SysSession",
    "SysUser",
    "SysUserRole",
    "Tool",
    "ToolAccessPolicy",
    "ToolCategory",
    "ToolComponentRegistry",
    "ToolPopularityDaily",
    "ToolRecentUsage",
    "ToolUsageDaily",
    "ToolUsageEvent",
    "ToolVersion",
]
