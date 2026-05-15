"""plan 按库 catalog 裁剪。"""
from __future__ import annotations

from core.infra.db.migration.execution_plan import (
    ExecutionPlan,
    MigrationStep,
    MigrationStepKind,
)
from core.infra.db.migration.introspection import DatabaseCatalog
from core.infra.db.migration.plan_prune import prune_plan_for_database


def _step(kind: MigrationStepKind, step_id: str, sql: str = "SQL", depends_on=()) -> MigrationStep:
    return MigrationStep(
        step_id=step_id,
        kind=kind,
        action_id="uk_t",
        sql=sql,
        depends_on=depends_on,
    )


def test_prune_skips_existing_create_table():
    plan = ExecutionPlan(
        steps=[
            _step(MigrationStepKind.CREATE_TABLE, "create_table:sys_t"),
            _step(
                MigrationStepKind.CREATE_INDEX,
                "create_index:sys_t:idx_a",
                depends_on=("create_table:sys_t",),
            ),
        ]
    )
    catalog = DatabaseCatalog(tables={"sys_t"}, indexes={"sys_t": {"idx_a"}})
    pruned = prune_plan_for_database(plan, catalog)
    assert pruned.steps == []
    assert any("create_table:sys_t" in w for w in pruned.warnings)


def test_prune_skips_add_column_but_keeps_missing_index():
    plan = ExecutionPlan(
        steps=[
            _step(MigrationStepKind.ADD_COLUMN, "add_column:sys_t:note"),
            _step(
                MigrationStepKind.CREATE_INDEX,
                "create_index:sys_t:idx_b",
                depends_on=("add_column:sys_t:note",),
            ),
        ]
    )
    catalog = DatabaseCatalog(
        tables={"sys_t"},
        columns={"sys_t": {"id", "note"}},
        indexes={"sys_t": set()},
    )
    pruned = prune_plan_for_database(plan, catalog)
    assert len(pruned.steps) == 1
    assert pruned.steps[0].step_id == "create_index:sys_t:idx_b"
    assert pruned.steps[0].depends_on == ()


def test_prune_skips_drop_missing_index():
    plan = ExecutionPlan(steps=[_step(MigrationStepKind.DROP_SECONDARY_INDEX, "drop_index:sys_t:idx_x")])
    catalog = DatabaseCatalog(tables={"sys_t"}, indexes={"sys_t": set()})
    pruned = prune_plan_for_database(plan, catalog)
    assert pruned.steps == []
