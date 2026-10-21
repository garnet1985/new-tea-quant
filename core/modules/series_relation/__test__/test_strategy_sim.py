"""strategy_sim 源：settings / loader / runner。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.series_relation.core.pipeline.load_strategy_sim import (
    StrategySimLoadError,
    load_strategy_sim_points,
)
from core.modules.series_relation.core.pipeline.runner import run_relation
from core.modules.series_relation.core.pipeline.transform import apply_transform
from core.modules.series_relation.core.settings.relation_settings import validate_settings
from core.modules.strategy.core.services.artifacts.consts import (
    EQUITY_CURVE_FILE,
    PRICE_INVESTMENTS_SUFFIX,
)

pytestmark = pytest.mark.force_run


def _lookup(key: str):
    catalog = {
        "index.kline.daily": {"meta": {"type": "time_series", "scope": "per_entity"}},
        "macro.lpr": {"meta": {"type": "time_series", "scope": "global"}},
    }
    return catalog.get(key)


def test_validate_strategy_sim_defaults_version_and_transform() -> None:
    raw = {
        "meta": {"key": "demo"},
        "series": [
            {
                "source": "strategy_sim",
                "strategy_key": "my_strategy_key",
                "layer": "portfolio",
                "metric": "equity",
            },
            {
                "data_key": "index.kline.daily",
                "entity_id": "000300.SH",
                "field": "close",
            },
        ],
    }
    settings, errors = validate_settings(raw, declaration_lookup=_lookup)
    assert errors == []
    assert settings is not None
    sim = settings["series"][0]
    assert sim["source"] == "strategy_sim"
    assert sim["strategy_key"] == "my_strategy_key"
    assert sim["strategy"] == "my_strategy_key"
    assert sim["version"] == "latest"
    assert sim["transform"] == "returns"
    assert settings["series"][1]["transform"] == "none"


def test_validate_strategy_alias_still_works() -> None:
    raw = {
        "meta": {"key": "demo"},
        "series": [
            {
                "source": "strategy_sim",
                "strategy": "path/like/id",
                "layer": "portfolio",
                "metric": "equity",
            }
        ],
    }
    settings, errors = validate_settings(raw, declaration_lookup=_lookup)
    assert errors == []
    assert settings is not None
    assert settings["series"][0]["strategy_key"] == "path/like/id"


def test_reject_portfolio_equity_with_entity_id() -> None:
    raw = {
        "meta": {"key": "x"},
        "series": [
            {
                "source": "strategy_sim",
                "strategy_key": "demo/foo",
                "layer": "portfolio",
                "metric": "equity",
                "entity_id": "000001.SZ",
            }
        ],
    }
    _, errors = validate_settings(raw, declaration_lookup=_lookup)
    assert any("entity_id" in e for e in errors)


def test_apply_transform_returns() -> None:
    pts = [("d1", 100.0), ("d2", 110.0), ("d3", 99.0)]
    out = apply_transform(pts, "returns")
    assert len(out) == 2
    assert out[0][0] == "d2"
    assert out[0][1] == pytest.approx(0.1)
    assert out[1][1] == pytest.approx((99.0 - 110.0) / 110.0)


def test_load_portfolio_equity_and_price_cum(tmp_path: Path) -> None:
    strategy_folder = tmp_path / "strat"
    vid = "3"
    port_dir = strategy_folder / "results" / "simulations" / vid / "portfolio"
    price_dir = strategy_folder / "results" / "simulations" / vid / "price"
    port_dir.mkdir(parents=True)
    (price_dir / "entities").mkdir(parents=True)
    (strategy_folder / "results" / "simulations" / "meta.json").write_text(
        json.dumps({"next_version_id": 4}), encoding="utf-8"
    )
    (port_dir / EQUITY_CURVE_FILE).write_text(
        json.dumps(
            [
                {"date": "20240102", "equity": 100.0},
                {"date": "20240103", "equity": 110.0},
                {"date": "20240104", "equity": 105.0},
            ]
        ),
        encoding="utf-8",
    )
    inv = price_dir / "entities" / f"600199.SH{PRICE_INVESTMENTS_SUFFIX}"
    inv.write_text(
        "opportunity_id,enter_date,enter_price,enter_price_hfq,exit_date,"
        "exit_price,exit_price_hfq,roi,holding_days,holding_trading_days,"
        "exit_reason,skip_reason,lifecycle,result\n"
        "1,20240102,10,10,20240103,11,11,0.10,1,1,tp,,complete,win\n"
        "2,20240103,11,11,20240105,9.9,9.9,-0.10,2,2,sl,,complete,loss\n",
        encoding="utf-8",
    )

    def resolve_folder(_key: str) -> Path:
        return strategy_folder

    eq_pts, eq_meta = load_strategy_sim_points(
        {
            "strategy_key": "demo/x",
            "version": "latest",
            "layer": "portfolio",
            "metric": "equity",
        },
        resolve_folder=resolve_folder,
    )
    assert eq_meta["resolved_version"] == "3"
    assert len(eq_pts) == 3
    assert eq_pts[1][1] == pytest.approx(110.0)

    roi_pts, _ = load_strategy_sim_points(
        {
            "strategy": "demo/x",
            "version": "3",
            "layer": "price",
            "metric": "cum_exit_roi",
            "entity_id": "600199.SH",
        },
        resolve_folder=resolve_folder,
    )
    assert roi_pts == [("20240103", 0.10), ("20240105", 0.0)]


def test_load_missing_layer_hard_fails(tmp_path: Path) -> None:
    strategy_folder = tmp_path / "strat"
    (strategy_folder / "results" / "simulations").mkdir(parents=True)
    (strategy_folder / "results" / "simulations" / "meta.json").write_text(
        json.dumps({"next_version_id": 1}), encoding="utf-8"
    )

    with pytest.raises(StrategySimLoadError):
        load_strategy_sim_points(
            {
                "strategy": "demo/x",
                "version": "latest",
                "layer": "portfolio",
                "metric": "equity",
            },
            resolve_folder=lambda _k: strategy_folder,
        )


def test_runner_with_strategy_sim(tmp_path: Path) -> None:
    def fake_sim(item, *, start_date="", end_date=""):
        _ = (start_date, end_date)
        layer = item.get("layer")
        if layer == "portfolio":
            pts = [(f"2024010{i}", 100.0 + i) for i in range(1, 9)]
        else:
            pts = [(f"2024010{i}", float(i) * 0.01) for i in range(1, 9)]
        return pts, {"resolved_version": "9"}

    def fake_rows(data_key, *, entity_id=""):
        _ = (data_key, entity_id)
        return [{"date": f"2024010{i}", "close": 1000.0 + i} for i in range(1, 9)]

    settings = {
        "meta": {"key": "mix"},
        "series": [
            {
                "source": "strategy_sim",
                "strategy_key": "demo/x",
                "version": "latest",
                "layer": "portfolio",
                "metric": "equity",
                "label": "组合",
                "transform": "returns",
            },
            {
                "source": "data_key",
                "data_key": "index.kline.daily",
                "entity_id": "000300.SH",
                "field": "close",
                "label": "指数",
                "transform": "returns",
                "scope": "per_entity",
            },
        ],
        "range": {"start_date": "", "end_date": ""},
        "normalize": "none",
        "fill": "none",
        "analyze": True,
    }
    result = run_relation(
        settings,
        output_dir=tmp_path / "out",
        load_rows=fake_rows,
        load_strategy_sim=fake_sim,
    )
    assert result["success"] is True
    meta = json.loads((tmp_path / "out" / "meta.json").read_text(encoding="utf-8"))
    assert meta["series"][0]["resolved_version"] == "9"
    assert meta["series"][0]["transform"] == "returns"
    report = (tmp_path / "out" / "report.txt").read_text(encoding="utf-8")
    assert "[sim " in report
    assert "portfolio.equity" in report
