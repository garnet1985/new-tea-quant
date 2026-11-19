"""Agent data tools：薄封装；域行为由 DataManager 覆盖。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.data.create_table import create_table
from core.modules.agent.core.code.tools.data.write_table_files import write_table_files


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


def test_agent_create_table_delegates(tables_root: Path) -> None:
    created = create_table({"key": "agent_tbl"})
    assert created.get("ok") is True, created
    assert (tables_root / "agent_tbl" / "schema.py").is_file()


def test_agent_write_rejects_sys(tables_root: Path) -> None:
    assert create_table({"key": "safe"}).get("ok") is True
    out = write_table_files(
        {
            "key": "safe",
            "schema_py": (
                'schema = {"storage_domain":"data","kind":"data",'
                '"name":"sys_data_hack","primaryKey":"id",'
                '"fields":[{"name":"id","type":"varchar","length":8,'
                '"isRequired":True,"nullable":False}]}\n'
            ),
        }
    )
    assert out.get("ok") is False
