"""app.admin.export — ORM model.

An administrative export job is stored in the frozen ``sys_export_job`` table
(see ``aicoding/sql/vctn-enterprise-ddl-v2.0.sql``). The admin management layer
owns **no table of its own**: the database structure has exactly one source of
truth, so this module re-exports the canonical model instead of declaring one.
"""

from __future__ import annotations

from app.system.files.model import SysExportJob

#: The one ORM model behind ``/admin/export/tasks``.
ExportJob = SysExportJob

__all__ = ["ExportJob", "SysExportJob"]
