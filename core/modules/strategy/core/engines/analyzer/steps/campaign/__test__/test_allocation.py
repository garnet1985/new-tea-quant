"""组合层 allocation：单独配置，不进战役共用 inputs。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.config import (
    AttributionConfig,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.config.inputs import (
    default_axes_shared,
)

pytestmark = pytest.mark.force_run

_SNAP = {
    "portfolio": {
        "initial_capital": 100000,
        "allocation": {
            "mode": "equal_capital",
            "max_portfolio_size": 10,
            "max_weight_per_stock": 0.2,
            "kelly_fraction": 0.5,
            "lots_per_trade": 1,
        },
    }
}


def test_missing_allocation_uses_defaults_and_stays_out_of_campaign() -> None:
    raw = {
        "inputs": {
            "rsi_oversold_threshold": {"values": [20, 25]},
        }
    }
    cfg = AttributionConfig.to_usable(raw, layer="portfolio")
    assert set(cfg.campaign_inputs) == {"core.rsi_oversold_threshold"}
    axes = cfg.allocation_axes(_SNAP)
    assert axes["portfolio.allocation.mode"] == (
        "equal_shares",
        "equal_capital",
    )
    assert 10 in axes["portfolio.allocation.max_portfolio_size"]
    assert axes["portfolio.initial_capital"] == (50000, 100000, 200000)
    assert "portfolio.allocation.kelly_fraction" in axes
    assert "portfolio.allocation.max_portfolio_size" not in default_axes_shared(_SNAP)
    snap = dict(_SNAP)
    snap["portfolio"] = {
        **_SNAP["portfolio"],
        "allocation": {**_SNAP["portfolio"]["allocation"], "default_cash": 10000},
    }
    assert "kelly" in cfg.allocation_axes(snap)["portfolio.allocation.mode"]


def test_declared_allocation_does_not_fill_omitted_axes() -> None:
    raw = {
        "inputs": {"rsi_oversold_threshold": {"values": [20]}},
        "allocation": {
            "mode": {"values": ["equal_shares", "kelly"]},
            "initial_capital": {"values": [100000, 300000]},
        },
    }
    cfg = AttributionConfig.to_usable(raw, layer="enumerate")
    axes = cfg.allocation_axes(_SNAP)
    assert set(axes) == {
        "portfolio.allocation.mode",
        "portfolio.initial_capital",
    }
    assert "portfolio.allocation.mode" not in cfg.campaign_inputs


def test_empty_allocation_opts_out() -> None:
    cfg = AttributionConfig.to_usable(
        {"inputs": {"rsi_oversold_threshold": {"values": [20]}}, "allocation": {}},
        layer="portfolio",
    )
    assert cfg.allocation_axes(_SNAP) == {}


def test_allocation_only_is_usable() -> None:
    cfg = AttributionConfig.to_usable(
        {
            "allocation": {
                "max_portfolio_size": {"values": [5, 10, 20]},
            }
        },
        layer="portfolio",
    )
    assert cfg.has_parameter
    assert cfg.campaign_inputs == {}
    assert cfg.allocation_axes(_SNAP)["portfolio.allocation.max_portfolio_size"] == (
        5,
        10,
        20,
    )


def test_portfolio_plan_is_allocation_oaat() -> None:
    from core.modules.strategy.core.engines.analyzer.steps.campaign.contrasts import (
        KnobContrasts,
    )
    from core.modules.strategy.core.engines.analyzer.steps.campaign.plan import (
        AttributionPlan,
    )
    from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
        StrategySettings,
    )

    snap = StrategySettings.to_usable(
        {
            "portfolio": {
                "initial_capital": 100000,
                "allocation": {
                    "mode": "equal_capital",
                    "max_portfolio_size": 10,
                    "default_cash": 10000,
                },
            }
        }
    )
    cfg = AttributionConfig.to_usable(
        {
            "inputs": {"rsi_oversold_threshold": {"values": [20, 30]}},
            "allocation": {
                "mode": {"values": ["equal_shares", "equal_capital", "kelly"]},
                "max_portfolio_size": {"values": [10, 20]},
            },
        },
        layer="portfolio",
    )
    cells = AttributionPlan.expand(snap, cfg, layer="portfolio")
    assert cells[0].overlay == {}
    overlays = [KnobContrasts.union_paths([cell.overlay]) for cell in cells[1:]]
    assert overlays == [
        ["portfolio.allocation.mode"],
        ["portfolio.allocation.mode"],
        ["portfolio.allocation.max_portfolio_size"],
    ]
    assert "core.rsi_oversold_threshold" not in {
        path for group in overlays for path in group
    }


def test_opportunity_selection_axis_is_portfolio_only() -> None:
    from core.modules.strategy.core.engines.analyzer.steps.campaign.contrasts import (
        KnobContrasts,
    )
    from core.modules.strategy.core.engines.analyzer.steps.campaign.plan import (
        AttributionPlan,
    )
    from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
        StrategySettings,
    )

    current = [{"rsi": "ASC"}, {"pe_percentile": "ASC"}]
    snap = StrategySettings.to_usable(
        {
            "portfolio": {
                "initial_capital": 100000,
                "allocation": {
                    "mode": "equal_capital",
                    "max_portfolio_size": 10,
                    "opportunity_selection": current,
                },
            }
        }
    )
    cfg = AttributionConfig.to_usable(
        {
            "inputs": {"rsi_oversold_threshold": {"values": [20, 30]}},
            "allocation": {
                "opportunity_selection": {
                    "values": [
                        current,
                        [],
                        [{"rsi": -70}, {"pe_percentile": -30}],
                    ]
                }
            },
        },
        layer="portfolio",
    )
    cells = AttributionPlan.expand(snap, cfg, layer="portfolio")
    assert cells[0].overlay == {}
    variants = [KnobContrasts.union_paths([cell.overlay]) for cell in cells[1:]]
    assert variants == [
        ["portfolio.allocation.opportunity_selection"],
        ["portfolio.allocation.opportunity_selection"],
    ]
    assert "core.rsi_oversold_threshold" not in {
        path for group in variants for path in group
    }


def test_unknown_axis_and_bad_mode_fail() -> None:
    with pytest.raises(ValueError, match="未知资金分配轴"):
        AttributionConfig.to_usable(
            {"allocation": {"stop_loss": {"values": [None]}}},
            layer="portfolio",
        )
    with pytest.raises(ValueError, match="取值须为列表"):
        AttributionConfig.to_usable(
            {"allocation": {"opportunity_selection": {"values": ["ASC"]}}},
            layer="portfolio",
        )
    with pytest.raises(ValueError, match="mode 只能是"):
        AttributionConfig.to_usable(
            {"allocation": {"mode": {"values": ["martingale"]}}},
            layer="portfolio",
        )
