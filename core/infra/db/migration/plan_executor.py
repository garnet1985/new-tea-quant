"""
按 :class:`~core.infra.db.migration.execution_plan.ExecutionPlan` 顺序执行 DDL / 数据脚本。

已写入 ``sys_schema_migration_log`` 的 ``step_id`` 会跳过（幂等）。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from core.infra.db.migration.execution_plan import (
    ExecutionPlan,
    MigrationStepKind,
    ordered_plan,
)
from core.infra.db.migration.migration_history import is_step_applied, record_step_applied

if TYPE_CHECKING:
    from core.infra.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def execute_plan(
    db: "DatabaseManager",
    plan: ExecutionPlan,
    *,
    script_context: Optional[dict] = None,
) -> None:
    """
    使用已初始化的 :class:`~core.infra.db.db_manager.DatabaseManager` 依次执行计划。

    DDL 步骤走 ``get_connection``；``RUN_DATA_SCRIPT`` 走 ``core.infra.update.db`` 注册表。
    """
    for step in ordered_plan(plan):
        if is_step_applied(db, step.step_id):
            logger.info("migration skip (already applied): %s", step.step_id)
            continue

        logger.info("migration %s [%s] action_id=%s", step.step_id, step.kind.value, step.action_id)

        if step.kind == MigrationStepKind.RUN_DATA_SCRIPT:
            script_id = step.script_action_id or step.action_id
            from core.infra.update.db.registry import run_data_script

            run_data_script(db, script_id, context=script_context)
        else:
            if not step.sql.strip():
                raise RuntimeError(f"迁移步骤 {step.step_id!r} 缺少 SQL")
            with db.get_connection() as conn:
                conn.execute(step.sql)

        record_step_applied(db, step)
