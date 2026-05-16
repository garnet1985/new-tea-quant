"""迁移历史表与数据脚本注册表。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.infra.db.migration.execution_plan import (
    ExecutionPlan,
    MigrationStep,
    MigrationStepKind,
)
from core.infra.db.migration.migration_history import (
    create_history_table_sql,
    is_step_applied,
    record_step_applied,
)
from core.infra.db.migration.plan_executor import execute_plan
from core.infra.update.db.registry import get_data_script, register_data_script


def _pg_config():
    return {
        "database_type": "postgresql",
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "database": "test",
            "user": "u",
            "password": "p",
            "pgsql_schema": "public",
        },
    }


def test_create_history_table_sql_postgresql():
    sql = create_history_table_sql(_pg_config())
    assert "sys_schema_migration_log" in sql
    assert "CREATE TABLE IF NOT EXISTS" in sql


def test_is_step_applied_queries_log():
    db = MagicMock()
    db.config = _pg_config()
    db.execute_sync_query.return_value = [{"ok": 1}]
    with patch(
        "core.infra.db.migration.migration_history.ensure_history_table",
        return_value=None,
    ):
        assert is_step_applied(db, "add_column:sys_t:note") is True
    db.execute_sync_query.assert_called_once()


@register_data_script("test_script_uk", description="test")
def _sample_script(db, context):
    context["ran"] = True


def test_register_and_get_data_script():
    entry = get_data_script("test_script_uk")
    assert entry is not None
    assert entry.action_id == "test_script_uk"


def test_execute_plan_skips_applied_steps():
    db = MagicMock()
    plan = ExecutionPlan(
        steps=[
            MigrationStep(
                step_id="add_column:sys_t:note",
                kind=MigrationStepKind.ADD_COLUMN,
                action_id="uk_t",
                sql="ALTER TABLE sys_t ADD COLUMN note VARCHAR(8)",
            )
        ]
    )
    with patch(
        "core.infra.db.migration.plan_executor.is_step_applied",
        return_value=True,
    ) as mock_applied:
        execute_plan(db, plan)
    mock_applied.assert_called_once_with(db, "add_column:sys_t:note")
    db.get_connection.assert_not_called()


def test_execute_plan_runs_data_script():
    db = MagicMock()
    ctx = {}
    plan = ExecutionPlan(
        steps=[
            MigrationStep(
                step_id="data_script:test_script_uk",
                kind=MigrationStepKind.RUN_DATA_SCRIPT,
                action_id="test_script_uk",
                script_action_id="test_script_uk",
            )
        ]
    )
    conn_cm = MagicMock()
    db.get_connection.return_value.__enter__ = MagicMock(return_value=conn_cm)
    db.get_connection.return_value.__exit__ = MagicMock(return_value=False)

    with patch(
        "core.infra.db.migration.plan_executor.is_step_applied",
        return_value=False,
    ), patch(
        "core.infra.db.migration.plan_executor.record_step_applied",
    ) as mock_record:
        execute_plan(db, plan, script_context=ctx)

    assert ctx.get("ran") is True
    mock_record.assert_called_once()
