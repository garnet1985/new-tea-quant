"""overlay None = 关：指纹换号；本层旋钮范围仍按前缀过滤。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.attribute import (
    EnumerateAttributeStep,
    PriceAttributeStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.plan import (
    AttributionPlan,
    AttributionTask,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.config import (
    AttributionConfig,
    SettingsOverlay,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.contrasts import (
    KnobContrasts,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

pytestmark = pytest.mark.force_run


def _snapshot() -> StrategySettings:
    return StrategySettings.to_usable(
        {
            "core": {
                "rsi_oversold_threshold": 20,
                "max_pe_percentile": 30,
                "min_netprofit_yoy": 0,
            },
            "goal": {
                "stop_loss": {
                    "stages": [{"ratio": -0.2, "close_invest": True}],
                },
                "take_profit": {
                    "stages": [{"ratio": 0.2, "close_invest": True}],
                },
            },
            "data": {"base": {"data_key": "stock.kline.daily"}},
        }
    )


def _fp(settings: StrategySettings) -> str:
    return FingerprintCalculator.to_execute_fingerprint(settings, ["000001.SZ"])


def test_overlay_none_stop_loss_changes_execute_fp() -> None:
    snapshot = _snapshot()
    off = SettingsOverlay.from_dict({"goal": {"stop_loss": None}}).merge_onto(snapshot)
    same_on = SettingsOverlay.from_dict(
        {
            "goal": {
                "stop_loss": {
                    "stages": [{"ratio": -0.2, "close_invest": True}],
                }
            }
        }
    ).merge_onto(snapshot)
    pe_off = SettingsOverlay.from_dict(
        {"core": {"max_pe_percentile": None}}
    ).merge_onto(snapshot)

    assert off.raw_settings["goal"]["stop_loss"] is None
    assert off.goal.stop_loss is None
    assert off.goal.take_profit is not None
    assert _fp(off) != _fp(snapshot)
    assert _fp(same_on) == _fp(snapshot)
    assert pe_off.goal.stop_loss is not None
    assert KnobContrasts.value_at(pe_off.raw_settings, "core.max_pe_percentile") is None
    assert _fp(pe_off) != _fp(snapshot)
    extracted = StrategySettings.extract_execute_settings(off)
    assert extracted["goal"]["stop_loss"] is None
    assert extracted["goal"]["take_profit"]


def test_declared_paths_treat_goal_block_as_atomic() -> None:
    assert KnobContrasts.declared_paths({"goal": {"stop_loss": None}}) == [
        "goal.stop_loss"
    ]
    assert KnobContrasts.declared_paths(
        {
            "goal": {
                "stop_loss": {
                    "stages": [{"ratio": -0.1, "close_invest": True}],
                }
            }
        }
    ) == ["goal.stop_loss"]
    assert KnobContrasts.declared_paths(
        {"core": {"max_pe_percentile": None, "rsi_oversold_threshold": 25}}
    ) == ["core.max_pe_percentile", "core.rsi_oversold_threshold"]


def test_price_layer_accepts_idea_knobs_ignores_portfolio() -> None:
    """价格层对照 core / goal / simulation，不收组合槽位。"""
    assert PriceAttributeStep.accepts_knob("simulation.price.opportunity_merge_gap")
    assert PriceAttributeStep.accepts_knob("core.max_pe_percentile")
    assert PriceAttributeStep.accepts_knob("goal.stop_loss")
    assert not PriceAttributeStep.accepts_knob(
        "portfolio.allocation.max_portfolio_size"
    )
    kept = PriceAttributeStep.filter_knobs(
        [
            "simulation.price.opportunity_merge_gap",
            "portfolio.allocation.max_portfolio_size",
            "core.max_pe_percentile",
        ]
    )
    assert kept == [
        "simulation.price.opportunity_merge_gap",
        "core.max_pe_percentile",
    ]


def test_enumerate_layer_drops_portfolio_knobs() -> None:
    assert not EnumerateAttributeStep.accepts_knob(
        "portfolio.allocation.max_portfolio_size"
    )
    assert EnumerateAttributeStep.accepts_knob("core.rsi_oversold_threshold")
    assert EnumerateAttributeStep.accepts_knob("goal.stop_loss")
    kept = EnumerateAttributeStep.filter_knobs(
        [
            "core.max_pe_percentile",
            "portfolio.allocation.max_portfolio_size",
        ]
    )
    assert kept == ["core.max_pe_percentile"]


def test_overlay_none_is_legal() -> None:
    snapshot = _snapshot()
    cfg = AttributionConfig.to_usable(
        {
            "inputs": {
                "rsi_oversold_threshold": {"values": [20]},
                "max_pe_percentile": {"values": [None]},
                "stop_loss": {"values": [None]},
            }
        },
        layer="enumerate",
    )
    assert cfg.has_layer_inputs
    cells = AttributionPlan.expand(snapshot, cfg, layer="enumerate")
    assert cells[0].overlay == {}
    pe_off = next(
        cell
        for cell in cells
        if KnobContrasts.value_at(cell.overlay, "core.max_pe_percentile")
        is None
        and cell.overlay
    )
    sl_off = next(
        cell
        for cell in cells
        if "goal" in (cell.overlay or {})
        and KnobContrasts.value_at(cell.overlay, "goal.stop_loss") is None
    )
    assert KnobContrasts.value_at(
        pe_off.effective.raw_settings, "core.max_pe_percentile"
    ) is None
    assert pe_off.effective.goal.stop_loss is not None
    assert sl_off.effective.goal.stop_loss is None
    assert sl_off.effective.goal.take_profit is not None
    knobs = KnobContrasts.read(
        pe_off.effective,
        KnobContrasts.union_paths(cell.overlay for cell in cells),
    )
    assert knobs["core.max_pe_percentile"] is None
    assert knobs["goal.stop_loss"] is not None
    tasks = AttributionTask.from_cells(cells, kind=SimulateKind.PORTFOLIO)
    assert tasks[0].kind is SimulateKind.PORTFOLIO
    assert tasks[0].steps == (
        SimulateKind.ENUMERATE,
        SimulateKind.PRICE_FACTOR,
        SimulateKind.PORTFOLIO,
    )
    assert cfg.parameter_mode == "oaat"


def test_attribution_settings_drops_fill_missing() -> None:
    cfg = AttributionConfig.to_usable(
        {
            "fill_missing": True,
            "inputs": {
                "rsi_oversold_threshold": {"values": [20]},
            },
            "rolling": {
                "windows": [{"start": "20230101", "end": "20231231"}],
                "fill_missing": False,
            },
        },
        layer="enumerate",
    )
    dumped = cfg.to_dict()
    assert "fill_missing" not in dumped
    assert "fill_missing" not in (dumped.get("rolling") or {})
    assert "steps" not in dumped
    assert "overlays" not in dumped
    assert "matrix" not in dumped
