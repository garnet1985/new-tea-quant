"""migration runner 与 migrate CLI（plan 路径，不连库）。"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.infra.db.migrate import main as migrate_main
from core.infra.db.migration.runner import (
    build_migration_plan,
    load_schemas_from_snapshot,
    run_schema_migration,
)


def _schema(name: str, uk: str, *, with_note: bool = False) -> dict:
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
    if with_note:
        fields.append(
            {
                "name": "note",
                "type": "varchar",
                "length": 8,
                "isRequired": False,
                "nullable": True,
                "description": "n",
            }
        )
    return {
        "update_key": uk,
        "name": name,
        "primaryKey": "id",
        "fields": fields,
        "indexes": [],
    }


def test_load_schemas_from_snapshot():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"sys_a": _schema("sys_a", "uk_a")}, f)
        path = Path(f.name)
    try:
        loaded = load_schemas_from_snapshot(path)
        assert "sys_a" in loaded
        assert loaded["sys_a"]["update_key"] == "uk_a"
    finally:
        path.unlink(missing_ok=True)


def test_run_schema_migration_plan_only():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        snap = root / "old.json"
        tables = root / "tables"
        tables.mkdir()
        (tables / "schema.py").write_text(
            'schema = ' + repr(_schema("sys_t", "uk_t", with_note=True)),
            encoding="utf-8",
        )
        snap.write_text(
            json.dumps({"sys_t": _schema("sys_t", "uk_t", with_note=False)}),
            encoding="utf-8",
        )
        result = run_schema_migration(
            pre_mirror_snapshot=snap,
            tables_dir=tables,
            apply=False,
        )
        assert result.plan is not None
        assert result.step_count >= 1
        assert result.applied is False


def test_migrate_cli_plan_subcommand():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        snap = root / "old.json"
        tables = root / "tables"
        tables.mkdir()
        (tables / "schema.py").write_text(
            'schema = ' + repr(_schema("sys_t", "uk_t")),
            encoding="utf-8",
        )
        snap.write_text(json.dumps({}), encoding="utf-8")
        code = migrate_main(
            [
                "plan",
                "--pre-mirror-snapshot",
                str(snap),
                "--tables-dir",
                str(tables),
                "--json",
            ]
        )
        assert code == 0


def test_build_migration_plan_empty_diff_skips_steps():
    s = _schema("sys_x", "uk_x")
    diff, plan = build_migration_plan({"sys_x": s}, {"sys_x": s})
    assert len(diff.non_unchanged()) == 0
    assert len(plan.steps) == 0
