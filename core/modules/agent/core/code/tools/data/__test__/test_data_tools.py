"""Agent data tools：薄封装；域行为由 DataManager / DataSourceManager 覆盖。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.data.create_data_source import create_data_source
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


@pytest.fixture()
def handlers_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "extensions" / "data_source"
    handlers = root / "handlers"
    template = handlers / "_template" / "example"
    template.mkdir(parents=True)
    (template / "handler.py").write_text(
        "from core.modules.data_source.contracts import DataSourceHooks\n"
        "class ExampleHooks(DataSourceHooks):\n"
        "    pass\n",
        encoding="utf-8",
    )
    (template / "settings.py").write_text("# placeholder\n", encoding="utf-8")
    (root / "mapping.py").write_text("DATA_SOURCES = {}\n", encoding="utf-8")
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_data_source_handlers_directory",
        lambda: handlers,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_data_source_mapping_path",
        lambda: root / "mapping.py",
    )
    return handlers


def test_agent_create_data_source_delegates(handlers_root: Path) -> None:
    created = create_data_source({"key": "agent_src"})
    assert created.get("ok") is True, created
    assert (handlers_root / "agent_src" / "handler.py").is_file()
    assert "AgentSrcHooks" in (
        handlers_root / "agent_src" / "handler.py"
    ).read_text(encoding="utf-8")
