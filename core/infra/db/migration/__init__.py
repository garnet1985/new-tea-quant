"""
Schema 迁移管线：期望 schema 之间的 diff、编译为 DDL 步骤、执行。

编排（何时调用）在 ``userspace/updater``；本包负责 diff → plan → execute。
"""
from core.infra.db.migration.schema_diff import (
    SchemaDiffResult,
    TableSchemaDiff,
    FieldChange,
    IndexChange,
    diff_expected_schemas,
)
from core.infra.db.migration.execution_plan import (
    ExecutionPlan,
    MigrationStep,
    MigrationStepKind,
    plan_from_schema_diff,
    MigrationPlanError,
    ordered_plan,
)
from core.infra.db.migration.migration_history import (
    ensure_history_table,
    is_step_applied,
    record_step_applied,
)
from core.infra.db.migration.plan_executor import execute_plan
from core.infra.db.migration.introspection import DatabaseCatalog, introspect_database
from core.infra.db.migration.plan_prune import prune_plan_for_database
from core.infra.db.migration.runner import (
    MigrationRunResult,
    build_migration_plan,
    default_pre_mirror_snapshot_path,
    load_current_table_schemas,
    load_schemas_from_snapshot,
    run_schema_migration,
)

__all__ = [
    "SchemaDiffResult",
    "TableSchemaDiff",
    "FieldChange",
    "IndexChange",
    "diff_expected_schemas",
    "ExecutionPlan",
    "MigrationStep",
    "MigrationStepKind",
    "plan_from_schema_diff",
    "MigrationPlanError",
    "ordered_plan",
    "execute_plan",
    "DatabaseCatalog",
    "introspect_database",
    "prune_plan_for_database",
    "ensure_history_table",
    "is_step_applied",
    "record_step_applied",
    "MigrationRunResult",
    "build_migration_plan",
    "default_pre_mirror_snapshot_path",
    "load_current_table_schemas",
    "load_schemas_from_snapshot",
    "run_schema_migration",
]
