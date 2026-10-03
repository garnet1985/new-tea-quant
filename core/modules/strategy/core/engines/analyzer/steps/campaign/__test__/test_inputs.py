"""按层 inputs：oaat / cross 展格。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.config import (
    AttributionConfig,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.config.inputs import (
    expand_axes,
    parse_axes,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.contrasts import (
    KnobContrasts,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.plan import (
    AttributionPlan,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

pytestmark = pytest.mark.force_run


def _snapshot() -> StrategySettings:
    return StrategySettings.to_usable(
        {
            "core": {
                "rsi_oversold_threshold": 20,
                "max_pe_percentile": 30,
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


def test_expand_axes_cross() -> None:
    axes = parse_axes(
        "enumerate",
        {
            "rsi_oversold_threshold": {"values": [20, 25]},
            "max_pe_percentile": {"values": [30, None]},
        },
        snapshot=_snapshot().raw_settings,
    )
    rows = expand_axes(axes, cross=True)
    assert len(rows) == 4
    pairs = {
        (
            KnobContrasts.value_at(row, "core.rsi_oversold_threshold"),
            KnobContrasts.value_at(row, "core.max_pe_percentile"),
        )
        for row in rows
    }
    assert pairs == {(20, 30), (20, None), (25, 30), (25, None)}


def test_plan_cross_mode() -> None:
    cfg = AttributionConfig.to_usable(
        {
            "enumerate": {
                "inputs": {
                    "rsi_oversold_threshold": {"values": [20, 25]},
                    "max_pe_percentile": {"values": [30, None]},
                },
                "cross": True,
            }
        },
        layer="enumerate",
    )
    assert cfg.parameter_mode == "cross"
    cells = AttributionPlan.expand(_snapshot(), cfg, layer="enumerate")
    # 基准 + 去重后的组合（与基准相同的 20/30 会并进基准）
    assert len(cells) >= 4
    pe_off = [
        cell
        for cell in cells
        if KnobContrasts.value_at(cell.overlay, "core.max_pe_percentile")
        is None
        and KnobContrasts.value_at(
            cell.overlay, "core.rsi_oversold_threshold"
        )
        == 25
    ]
    assert len(pe_off) == 1
    assert pe_off[0].effective.goal.stop_loss is not None


def test_plan_oaat_baseline() -> None:
    cfg = AttributionConfig.to_usable(
        {
            "enumerate": {
                "inputs": {
                    "rsi_oversold_threshold": {"values": [25]},
                    "max_pe_percentile": {"values": [None]},
                },
                "cross": False,
            }
        },
        layer="enumerate",
    )
    assert cfg.parameter_mode == "inputs"
    cells = AttributionPlan.expand(_snapshot(), cfg, layer="enumerate")
    assert cells[0].overlay == {}
    assert len(cells) == 3  # 基准 + rsi25 + pe None


def test_reject_legacy_overlays() -> None:
    with pytest.raises(ValueError, match="overlays"):
        AttributionConfig.to_usable(
            {"overlays": [{"core": {"rsi_oversold_threshold": 20}}]},
            layer="enumerate",
        )


def test_reject_legacy_matrix() -> None:
    with pytest.raises(ValueError, match="matrix"):
        AttributionConfig.to_usable(
            {
                "matrix": {
                    "core": {"rsi_oversold_threshold": [20, 25]},
                }
            },
            layer="enumerate",
        )


def test_versions_exclusive_with_inputs() -> None:
    with pytest.raises(ValueError, match="versions"):
        AttributionConfig.to_usable(
            {
                "versions": [3],
                "enumerate": {
                    "inputs": {
                        "rsi_oversold_threshold": {"values": [20]},
                    }
                },
            },
            layer="enumerate",
        )


def test_hook_goal_skipped_in_defaults() -> None:
    from core.modules.strategy.core.engines.analyzer.steps.campaign.config.inputs import (
        default_axes_for_layer,
        merge_user_and_defaults,
    )

    snap = {
        "goal": {
            "stop_loss": {
                "stages": [
                    {
                        "custom": "is_stop_loss",
                        "description": "钩子止损",
                        "close_invest": True,
                    }
                ],
            },
            "take_profit": {
                "stages": [{"ratio": 0.2, "close_invest": True}],
            },
        },
        "core": {"rsi_oversold_threshold": 20},
    }
    defaults = default_axes_for_layer("enumerate", snap)
    assert "goal.stop_loss" not in defaults
    assert "goal.take_profit" in defaults
    with pytest.raises(ValueError, match="钩子"):
        merge_user_and_defaults(
            "enumerate",
            {"stop_loss": {"values": [-0.2, None]}},
            snap,
        )


def test_goal_scalar_shorthand() -> None:
    cfg = AttributionConfig.to_usable(
        {
            "enumerate": {
                "inputs": {
                    "stop_loss": {"values": [None, -0.15]},
                }
            }
        },
        layer="enumerate",
    )
    cells = AttributionPlan.expand(_snapshot(), cfg, layer="enumerate")
    ratios = []
    for cell in cells:
        if not cell.overlay:
            continue
        sl = KnobContrasts.value_at(cell.overlay, "goal.stop_loss")
        if sl is None:
            ratios.append(None)
        elif isinstance(sl, dict):
            stages = sl.get("stages") or []
            ratios.append(stages[0].get("ratio") if stages else None)
    assert None in ratios
    assert -0.15 in ratios
