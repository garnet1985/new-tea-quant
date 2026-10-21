"""cli list catalog 编排（不连真实 DB / 全量 discovery）。"""
from __future__ import annotations

import json

import pytest

from core.modules.cli.user import list_catalog
from core.modules.cli.user.abbrev import UserAbbrev
from core.modules.cli.user.parser import UserParser

pytestmark = pytest.mark.force_run


def test_expand_ls_alias() -> None:
    assert UserAbbrev.expand_argv(["ls", "stock.area"]) == ["list", "stock.area"]
    assert UserAbbrev.expand_argv(["ls", "datakeys"]) == ["list", "datakeys"]


def test_parse_list_resource_and_json() -> None:
    args = UserParser.parse_args(["list", "stock.market", "--json"])
    assert args.command == "list"
    assert args.resource == "stock.market"
    assert args.json is True


def test_parse_list_tag_nested() -> None:
    args = UserParser.parse_args(["list", "tag.demo/market_cap_tier"])
    assert args.command == "list"
    assert args.resource == "tag.demo/market_cap_tier"


def test_run_unknown_resource_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    code = list_catalog.run("nope")
    assert code == 1
    err = capsys.readouterr().out
    assert "未知 resource" in err
    assert "datakeys" in err
    assert "tags" in err


def test_run_stock_area_uses_dm(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def _fake(dim):
        assert dim == "area"
        return {"area": [{"value": "广东", "label": "广东"}]}

    monkeypatch.setattr(list_catalog, "_load_stock_options", _fake)
    code = list_catalog.run("stock.area")
    assert code == 0
    out = capsys.readouterr().out
    assert "[area]" in out
    assert "广东" in out


def test_run_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        list_catalog,
        "_load_stock_options",
        lambda dim: {"list_status": [{"value": "L", "label": "上市"}]},
    )
    code = list_catalog.run("stock.list_status", as_json=True)
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["list_status"][0]["value"] == "L"


def test_run_datakeys(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        list_catalog,
        "_load_datakeys",
        lambda: [
            {
                "key": "stock.kline.daily",
                "type": "time_series",
                "scope": "per_entity",
                "time_series": True,
                "per_entity": True,
                "display_name": "日K",
            }
        ],
    )
    list_catalog._STATIC_LOADERS.clear()
    code = list_catalog.run("datakeys")
    assert code == 0
    out = capsys.readouterr().out
    assert "[datakeys]" in out
    assert "stock.kline.daily" in out
    assert "time_series" in out
    assert "per_entity" in out

    # 单数别名 → 规范复数名输出
    list_catalog._STATIC_LOADERS.clear()
    assert list_catalog.run("datakey", as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "datakeys" in payload
    assert "datakey" not in payload


def test_run_tag_definitions(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        list_catalog,
        "_load_tag_definitions",
        lambda tag_id: (
            [
                {
                    "value": "high_cap",
                    "name": "high_cap",
                    "display_name": "高市值",
                    "description": "",
                }
            ],
            None,
        )
        if tag_id == "demo/x"
        else ([], "未找到 tag: missing"),
    )
    assert list_catalog.run("tag.missing") == 1
    code = list_catalog.run("tag.demo/x")
    assert code == 0
    out = capsys.readouterr().out
    assert "high_cap" in out
    assert "高市值" in out


def test_run_indicators_and_tables(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        list_catalog,
        "_load_indicators",
        lambda: [{"value": "rsi", "name": "rsi"}],
    )
    monkeypatch.setattr(
        list_catalog,
        "_load_tables",
        lambda: [{"value": "sys_data_stock_list", "name": "sys_data_stock_list"}],
    )
    list_catalog._STATIC_LOADERS.clear()
    assert list_catalog.run("indicators") == 0
    assert "rsi" in capsys.readouterr().out
    assert list_catalog.run("tables", as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tables"][0]["value"] == "sys_data_stock_list"

    list_catalog._STATIC_LOADERS.clear()
    assert list_catalog.run("table", as_json=True) == 0
    assert "tables" in json.loads(capsys.readouterr().out)


def test_run_strategies(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        list_catalog,
        "_load_strategies",
        lambda: [
            {
                "key": "rsi_v1",
                "is_enabled": True,
                "name": "RSI 演示",
                "id": "demo/rsi",
            }
        ],
    )
    list_catalog._STATIC_LOADERS.clear()
    assert list_catalog.run("strategies") == 0
    out = capsys.readouterr().out
    assert "[strategies]" in out
    assert "rsi_v1" in out
    assert "is_enabled=True" in out
    assert "RSI 演示" in out
    assert out.index("rsi_v1") < out.index("is_enabled=True") < out.index("id=demo/rsi")

    list_catalog._STATIC_LOADERS.clear()
    assert list_catalog.run("strategy") == 0
    assert "[strategies]" in capsys.readouterr().out


def test_run_tags_alias(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        list_catalog,
        "_load_tags",
        lambda: [
            {
                "key": "market_cap_tier",
                "is_enabled": True,
                "name": "市值分层",
                "id": "demo/market_cap_tier",
            }
        ],
    )
    list_catalog._STATIC_LOADERS.clear()
    assert list_catalog.run("tags") == 0
    assert "[tags]" in capsys.readouterr().out
    list_catalog._STATIC_LOADERS.clear()
    assert list_catalog.run("tag") == 0
    assert "[tags]" in capsys.readouterr().out


def test_known_resources_includes_plural_and_aliases() -> None:
    list_catalog._STATIC_LOADERS.clear()
    names = list_catalog.known_resources()
    for item in (
        "datakeys",
        "tags",
        "strategies",
        "indicators",
        "tables",
        "datakey",
        "tag",
        "strategy",
        "indicator",
        "table",
        "stock.area",
        "stock",
    ):
        assert item in names
