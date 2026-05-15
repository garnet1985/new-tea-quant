"""
升级迁移编排：加载快照与新 schema → diff → plan →（可选）执行。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.db.db_manager import DatabaseManager
from core.infra.db.migration.introspection import introspect_database
from core.infra.db.migration.plan_prune import prune_plan_for_database
from core.infra.db.schema_management.schema_manager import SchemaManager
from core.infra.db.migration.schema_diff import SchemaDiffResult, diff_expected_schemas
from core.infra.db.migration.execution_plan import (
    ExecutionPlan,
    MigrationPlanError,
    ordered_plan,
    plan_from_schema_diff,
)
from core.infra.db.migration.plan_executor import execute_plan

logger = logging.getLogger(__name__)

DEFAULT_PRE_MIRROR_FILENAME = "pre_mirror_core_table_schemas.json"


@dataclass
class MigrationRunResult:
    """单次 ``run_schema_migration`` 的结果（plan 驻内存）。"""

    old_schema_count: int = 0
    new_schema_count: int = 0
    diff: Optional[SchemaDiffResult] = None
    plan: Optional[ExecutionPlan] = None
    applied: bool = False
    skipped_reason: Optional[str] = None
    step_count: int = 0


def load_schemas_from_snapshot(path: Path) -> Dict[str, Dict[str, Any]]:
    """从 updater 写入的 JSON 加载 ``{表名: schema dict}``。"""
    p = path.resolve()
    if not p.is_file():
        raise FileNotFoundError(f"schema 快照不存在: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"schema 快照根节点须为 object: {p}")
    out: Dict[str, Dict[str, Any]] = {}
    for key, val in raw.items():
        if isinstance(val, dict) and val.get("name"):
            out[str(key)] = val
    return out


def default_pre_mirror_snapshot_path(repo_root: Path) -> Path:
    return (
        repo_root
        / "userspace"
        / ".ntq"
        / "update"
        / "cache"
        / DEFAULT_PRE_MIRROR_FILENAME
    ).resolve()


def load_current_table_schemas(
    repo_root: Optional[Path] = None,
    *,
    tables_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """从当前 ``core/tables``（或指定目录）加载新版期望 schema。"""
    if tables_dir is not None:
        td = str(tables_dir.resolve())
    elif repo_root is not None:
        td = str((repo_root / "core" / "tables").resolve())
    else:
        from core.infra.project_context import PathManager

        td = str(PathManager.core() / "tables")
    sm = SchemaManager(tables_dir=td)
    return sm.load_all_schemas()


def build_migration_plan(
    old_schemas: Dict[str, Dict[str, Any]],
    new_schemas: Dict[str, Dict[str, Any]],
    *,
    database_type: str = "postgresql",
    db: Optional[DatabaseManager] = None,
) -> tuple[SchemaDiffResult, ExecutionPlan]:
    """diff + plan；若提供 ``db`` 则 introspection 后裁剪已在库中的步骤。"""
    diff = diff_expected_schemas(old_schemas, new_schemas)
    sm = SchemaManager(database_type=database_type)
    plan = plan_from_schema_diff(
        diff,
        sm,
        old_schemas=old_schemas,
        new_schemas=new_schemas,
    )
    if db is not None:
        catalog = introspect_database(db)
        plan = prune_plan_for_database(plan, catalog)
    return diff, plan


def run_schema_migration(
    *,
    pre_mirror_snapshot: Path,
    repo_root: Optional[Path] = None,
    tables_dir: Optional[Path] = None,
    apply: bool = True,
    against_database: bool = False,
    database_type: Optional[str] = None,
) -> MigrationRunResult:
    """
    完整升级迁移：旧期望（快照）vs 新期望（当前 ``core/tables``）。

    Args:
        pre_mirror_snapshot: 镜像前写入的 JSON 路径
        repo_root: 用于定位 ``core/tables``；省略时用 ``PathManager``
        tables_dir: 显式指定 schema 目录（覆盖 ``repo_root/core/tables``）
        apply: ``True`` 时执行 DDL；``False`` 仅生成 plan
        against_database: ``True`` 时连库 introspection 并裁剪 plan（``apply=False`` 时用于 dry-run / 预览）
        database_type: 方言；连库时以 ``DatabaseManager`` 配置为准
    """
    result = MigrationRunResult()
    old_schemas = load_schemas_from_snapshot(pre_mirror_snapshot)
    new_schemas = load_current_table_schemas(repo_root, tables_dir=tables_dir)
    result.old_schema_count = len(old_schemas)
    result.new_schema_count = len(new_schemas)

    if not old_schemas and not new_schemas:
        result.skipped_reason = "old 与 new schema 均为空"
        return result

    db_type = (database_type or "postgresql").lower()
    use_db = apply or against_database

    if use_db:
        db = DatabaseManager()
        db.initialize()
        try:
            db_type = db.config.get("database_type", db_type)
            diff, plan = build_migration_plan(
                old_schemas,
                new_schemas,
                database_type=db_type,
                db=db,
            )
            result.diff = diff
            result.plan = plan
            result.step_count = len(ordered_plan(plan))

            if result.step_count == 0 and not plan.warnings:
                result.skipped_reason = "无 schema 结构变更（或与库已对齐）"
                return result

            for w in plan.warnings:
                logger.warning("migration plan: %s", w)

            if apply:
                execute_plan(db, plan)
                result.applied = True
        finally:
            db.close()
        return result

    diff, plan = build_migration_plan(old_schemas, new_schemas, database_type=db_type)
    result.diff = diff
    result.plan = plan
    result.step_count = len(ordered_plan(plan))

    if result.step_count == 0 and not plan.warnings:
        result.skipped_reason = "无 schema 结构变更"

    for w in plan.warnings:
        logger.warning("migration plan: %s", w)

    return result
