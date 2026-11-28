"""Agent data tools：薄封装；域行为由 DataManager / DataSourceManager 覆盖。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.data.create_data_contract import (
    create_data_contract,
)
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
        "from core.infra.db.contracts import DbBaseModel\n"
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


@pytest.fixture()
def contracts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "extensions" / "data_contract"
    example = root / "contract_example"
    example.mkdir(parents=True)
    (example / "declaration.py").write_text("X = {}\n", encoding="utf-8")
    (example / "loader.py").write_text(
        "from core.modules.data_contract.contracts import BaseDataContractLoader\n"
        "class MyCustomDataLoader(BaseDataContractLoader):\n"
        "    def load(self, params):\n"
        "        return []\n",
        encoding="utf-8",
    )
    (root / "data_keys.py").write_text(
        "class USER_DATA_KEY:\n    pass\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_data_contract_root",
        lambda: root,
    )
    return root


def test_agent_create_data_contract_delegates(contracts_root: Path) -> None:
    created = create_data_contract(
        {"key": "agent_feed", "data_key": "agent.feed.data"}
    )
    assert created.get("ok") is True, created
    assert (contracts_root / "agent_feed" / "declaration.py").is_file()
    assert "agent.feed.data" in (
        contracts_root / "agent_feed" / "declaration.py"
    ).read_text(encoding="utf-8")


def test_list_indicators_ok() -> None:
    from core.modules.agent.core.code.tools.data.inspect_data import list_indicators

    out = list_indicators({})
    assert out.get("ok") is True, out
    assert out.get("count", 0) >= 1
    assert any(row.get("value") == "ma" for row in out.get("indicators") or [])


def test_list_stock_pool_dimensions_rejects_bad_dim() -> None:
    from core.modules.agent.core.code.tools.data.inspect_data import (
        list_stock_pool_dimensions,
    )

    out = list_stock_pool_dimensions({"dim": "sector"})
    assert out.get("ok") is False
    assert "dim" in str(out.get("error") or "")


def test_start_data_renew_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.modules.agent.core.code.tools.data import renew as renew_mod

    monkeypatch.setattr(
        renew_mod.JobPipeline,
        "get_running_job",
        staticmethod(lambda: {"kind": "data_renew", "job_id": "x"}),
    )
    out = renew_mod.start_data_renew({})
    assert out.get("ok") is False
    assert "进行中" in str(out.get("error") or "")


def test_read_renew_progress_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.modules.agent.core.code.tools.data import renew as renew_mod

    monkeypatch.setattr(
        renew_mod.DataSourceManager,
        "read_renew_ui_status",
        staticmethod(lambda: {"tasks": [], "progress": {"pct": 0}}),
    )
    monkeypatch.setattr(
        renew_mod.JobPipeline,
        "get_running_job",
        staticmethod(lambda: None),
    )
    with renew_mod._LOCK:
        renew_mod._ACTIVE = None
    out = renew_mod.read_renew_progress({})
    assert out.get("ok") is True, out
    assert out.get("running") is False


def test_preview_data_rows_unsupported_key() -> None:
    from core.modules.agent.core.code.tools.data.preview_data import preview_data_rows

    out = preview_data_rows(
        {"data_key": "macro.gdp", "entity_id": "CN"}
    )
    assert out.get("ok") is False
    assert "暂不支持" in str(out.get("error") or "")


def test_preview_data_rows_kline(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.modules.agent.core.code.tools.data import preview_data as preview_mod

    class _Kline:
        def load(self, stock_id, term="daily", start_date=None, end_date=None):
            assert stock_id == "600036.SH"
            return [
                {"trade_date": "20240101", "close": 30.0},
                {"trade_date": "20240102", "close": 31.0},
            ]

    class _Stock:
        kline = _Kline()

    class _DM:
        stock = _Stock()

    monkeypatch.setattr(preview_mod, "DataManager", lambda: _DM())
    out = preview_mod.preview_data_rows(
        {"data_key": "stock.kline.daily", "entity_id": "600036.SH", "limit": 1}
    )
    assert out.get("ok") is True, out
    assert out.get("returned") == 1
    assert out["rows"][0]["close"] == 31.0
