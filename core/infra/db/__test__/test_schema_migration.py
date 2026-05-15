"""schema 迁移：diff → plan →（执行接口单独集成测试）。"""
from __future__ import annotations

import pytest

from core.infra.db.schema_management.schema_manager import SchemaManager
from core.infra.db.migration.schema_diff import diff_expected_schemas
from core.infra.db.migration.execution_plan import (
    plan_from_schema_diff,
    MigrationPlanError,
    ordered_plan,
)


def _minimal_table(name: str, update_key: str, extra_field: bool = False) -> dict:
    fields = [
        {
            "name": "id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "autoIncrement": True,
            "description": "pk",
        },
    ]
    if extra_field:
        fields.append(
            {
                "name": "note",
                "type": "varchar",
                "length": 32,
                "isRequired": False,
                "nullable": True,
                "description": "note",
            }
        )
    return {
        "update_key": update_key,
        "name": name,
        "primaryKey": "id",
        "fields": fields,
        "indexes": [],
    }


def test_diff_added_table():
    old = {}
    new = {"sys_x": _minimal_table("sys_x", "uk_x")}
    d = diff_expected_schemas(old, new)
    assert len(d.non_unchanged()) == 1
    assert d.tables[0].kind == "added"


def test_diff_removed_table():
    old = {"sys_x": _minimal_table("sys_x", "uk_x")}
    new = {}
    d = diff_expected_schemas(old, new)
    assert d.non_unchanged()[0].kind == "removed"


def test_diff_add_column():
    t_old = _minimal_table("sys_x", "uk_x", extra_field=False)
    t_new = _minimal_table("sys_x", "uk_x", extra_field=True)
    d = diff_expected_schemas({"sys_x": t_old}, {"sys_x": t_new})
    mod = [x for x in d.tables if x.kind == "modified"][0]
    assert len(mod.field_changes) == 1
    assert mod.field_changes[0].kind == "add"


def test_plan_new_table_sql():
    sm = SchemaManager(database_type="postgresql")
    old = {}
    new = {"sys_x": _minimal_table("sys_x", "uk_x")}
    diff = diff_expected_schemas(old, new)
    plan = plan_from_schema_diff(diff, sm, old_schemas=old, new_schemas=new)
    assert len(plan.steps) == 1
    assert "CREATE TABLE" in plan.steps[0].sql.upper()


def test_plan_add_column_orders_drop_before_recreate_index():
    sm = SchemaManager(database_type="postgresql")
    t_old = {
        "update_key": "uk_t",
        "name": "sys_t",
        "primaryKey": "id",
        "fields": [
            {
                "name": "id",
                "type": "int",
                "isRequired": True,
                "nullable": False,
                "autoIncrement": True,
                "description": "pk",
            },
        ],
        "indexes": [{"name": "idx_a", "fields": ["id"], "unique": False}],
    }
    t_new = {
        "update_key": "uk_t",
        "name": "sys_t",
        "primaryKey": "id",
        "fields": [
            {
                "name": "id",
                "type": "int",
                "isRequired": True,
                "nullable": False,
                "autoIncrement": True,
                "description": "pk",
            },
            {
                "name": "note",
                "type": "varchar",
                "length": 16,
                "isRequired": False,
                "nullable": True,
                "description": "n",
            },
        ],
        "indexes": [{"name": "idx_a", "fields": ["id"], "unique": False}],
    }
    diff = diff_expected_schemas({"sys_t": t_old}, {"sys_t": t_new})
    plan = plan_from_schema_diff(diff, sm, old_schemas={"sys_t": t_old}, new_schemas={"sys_t": t_new})
    ordered = ordered_plan(plan)
    kinds = [s.kind.value for s in ordered]
    assert kinds[0] == "drop_secondary_index"
    assert "add_column" in kinds
    idx_create_pos = kinds.index("create_index")
    add_pos = kinds.index("add_column")
    assert idx_create_pos > add_pos


def test_plan_rejects_drop_column():
    sm = SchemaManager(database_type="postgresql")
    t_new = _minimal_table("sys_x", "uk_x", extra_field=False)
    t_old = _minimal_table("sys_x", "uk_x", extra_field=True)
    diff = diff_expected_schemas({"sys_x": t_old}, {"sys_x": t_new})
    with pytest.raises(MigrationPlanError):
        plan_from_schema_diff(diff, sm, old_schemas={"sys_x": t_old}, new_schemas={"sys_x": t_new})
