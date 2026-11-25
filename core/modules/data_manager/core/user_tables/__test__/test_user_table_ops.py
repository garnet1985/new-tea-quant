"""UserTableOps：userspace scaffold + core 守卫。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.data_manager import DataManager
from core.modules.data_manager.core.user_tables import UserTableOps


@pytest.fixture()
def tables_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tables = tmp_path / "extensions" / "tables"
    template = tables / "_template" / "empty_table"
    template.mkdir(parents=True)
    (template / "schema.py").write_text(
        'schema = {\n'
        '    "storage_domain": "strategy",\n'
        '    "kind": "data",\n'
        '    "name": "cust_data_empty_table",\n'
        '    "primaryKey": "id",\n'
        '    "fields": [{"name": "id", "type": "varchar", "length": 64,\n'
        '                "isRequired": True, "nullable": False}],\n'
        '}\n',
        encoding="utf-8",
    )
    (template / "model.py").write_text(
        "from core.infra.db import DbBaseModel\n"
        "from .schema import schema as _schema\n"
        "class EmptyTableModel(DbBaseModel):\n"
        "    def load_schema(self):\n"
        "        return _schema\n"
        "    def __init__(self, db=None):\n"
        "        super().__init__(_schema['name'], db)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_extensions_tables_directory",
        lambda: tables,
    )
    return tables


def test_scaffold_user_table(tables_root: Path) -> None:
    out = DataManager.scaffold_user_table(key="my_signals", kind="data")
    assert out.get("ok") is True, out
    dest = tables_root / "my_signals"
    assert (dest / "schema.py").is_file()
    assert "cust_data_my_signals" in (dest / "schema.py").read_text(encoding="utf-8")
    assert "MySignalsModel" in (dest / "model.py").read_text(encoding="utf-8")


def test_scaffold_rejects_sys_name(tables_root: Path) -> None:
    out = DataManager.scaffold_user_table(
        key="bad", table_name="sys_data_stock_list"
    )
    assert out.get("ok") is False
    assert out.get("requires_confirm") is True
    assert not (tables_root / "bad").exists()


def test_write_rejects_sys_schema(tables_root: Path) -> None:
    assert DataManager.scaffold_user_table(key="safe").get("ok") is True
    out = DataManager.write_user_table_files(
        key="safe",
        schema_py=(
            'schema = {\n'
            '  "storage_domain": "data",\n'
            '  "kind": "data",\n'
            '  "name": "sys_data_hack",\n'
            '  "primaryKey": "id",\n'
            '  "fields": [{"name": "id", "type": "varchar", "length": 8,\n'
            '              "isRequired": True, "nullable": False}],\n'
            '}\n'
        ),
    )
    assert out.get("ok") is False
    assert "系统表" in str(out.get("error") or "")


def test_refuse_core_structural() -> None:
    blocked = UserTableOps.refuse_core_structural("sys_data_stock_list")
    assert blocked is not None
    assert blocked.get("requires_confirm") is True
    assert UserTableOps.refuse_core_structural("cust_data_ok") is None
