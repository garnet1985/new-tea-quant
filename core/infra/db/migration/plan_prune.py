"""
根据 :class:`~core.infra.db.migration.introspection.DatabaseCatalog` 裁剪执行计划，跳过已在库中的 DDL。
"""
from __future__ import annotations

from typing import List, Set, Tuple

from core.infra.db.migration.execution_plan import (
    ExecutionPlan,
    MigrationStep,
    MigrationStepKind,
    ordered_plan,
)
from core.infra.db.migration.introspection import DatabaseCatalog


def _parse_step_targets(step: MigrationStep) -> Tuple[str, str | None]:
    """从 ``step_id`` 解析 ``(table_name, detail)``；``detail`` 为列名或索引名。"""
    parts = step.step_id.split(":", 2)
    if len(parts) < 2:
        return "", None
    table = parts[1]
    detail = parts[2] if len(parts) > 2 else None
    return table, detail


def _should_skip_step(step: MigrationStep, catalog: DatabaseCatalog) -> bool:
    table, detail = _parse_step_targets(step)
    if not table:
        return False

    if step.kind == MigrationStepKind.RUN_DATA_SCRIPT:
        return False

    if step.kind == MigrationStepKind.CREATE_TABLE:
        return catalog.has_table(table)

    if step.kind == MigrationStepKind.ADD_COLUMN:
        return detail is not None and catalog.has_column(table, detail)

    if step.kind == MigrationStepKind.CREATE_INDEX:
        return detail is not None and catalog.has_index(table, detail)

    if step.kind == MigrationStepKind.DROP_SECONDARY_INDEX:
        return detail is not None and not catalog.has_index(table, detail)

    return False


def prune_plan_for_database(plan: ExecutionPlan, catalog: DatabaseCatalog) -> ExecutionPlan:
    """
    返回新 :class:`ExecutionPlan`：跳过库中已满足的步骤，并收紧 ``depends_on``。

    被跳过的步骤会写入 ``warnings``（便于日志排障）。
    """
    skipped_ids: Set[str] = set()
    kept: List[MigrationStep] = []
    warnings = list(plan.warnings)

    for step in ordered_plan(plan):
        if _should_skip_step(step, catalog):
            skipped_ids.add(step.step_id)
            table, detail = _parse_step_targets(step)
            warnings.append(
                f"跳过 {step.step_id}：库中已存在 "
                f"{'表' if step.kind == MigrationStepKind.CREATE_TABLE else detail!r} "
                f"({table})"
            )
            continue

        new_deps = tuple(d for d in step.depends_on if d and d not in skipped_ids)
        if new_deps != step.depends_on:
            step = MigrationStep(
                step_id=step.step_id,
                kind=step.kind,
                action_id=step.action_id,
                sql=step.sql,
                depends_on=new_deps,
                script_action_id=step.script_action_id,
            )
        kept.append(step)

    return ExecutionPlan(steps=kept, warnings=warnings)
