"""matrix 是各轴笛卡尔积；旧的 list 写法要改成 overlays。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.cells import (
    CellExpander,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.config import (
    AttributionSettings,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.contrasts import (
    KnobContrasts,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.grid import (
    SettingsMatrix,
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


def test_expand_cartesian_includes_all_axes() -> None:
    raw = {
        "core": {
            "rsi_oversold_threshold": [20, 25],
            "max_pe_percentile": [30, None],
        }
    }
    rows = SettingsMatrix.expand(raw)
    assert len(rows) == 4
    pairs = {
        (
            KnobContrasts.value_at(row, "core.rsi_oversold_threshold"),
            KnobContrasts.value_at(row, "core.max_pe_percentile"),
        )
        for row in rows
    }
    assert pairs == {(20, 30), (20, None), (25, 30), (25, None)}
    assert all("goal" not in row for row in rows)


def test_cell_expander_matrix_mode() -> None:
    cfg = AttributionSettings.to_usable(
        {
            "steps": ["enumerate", "price_factor", "portfolio"],
            "matrix": {
                "core": {
                    "rsi_oversold_threshold": [20, 25],
                    "max_pe_percentile": [30, None],
                }
            },
        }
    )
    assert cfg.parameter_mode == "matrix"
    cells = CellExpander.expand(_snapshot(), cfg)
    assert len(cells) == 4
    pe_off = [
        cell
        for cell in cells
        if KnobContrasts.value_at(cell.overlay, "core.max_pe_percentile") is None
        and KnobContrasts.value_at(cell.overlay, "core.rsi_oversold_threshold") == 25
    ]
    assert len(pe_off) == 1
    assert pe_off[0].effective.goal.stop_loss is not None
    assert KnobContrasts.value_at(
        pe_off[0].effective.raw_settings, "core.max_pe_percentile"
    ) is None


def test_legacy_matrix_list_is_rejected() -> None:
    with pytest.raises(ValueError, match="overlays"):
        AttributionSettings.to_usable(
            {
                "steps": ["enumerate"],
                "matrix": [{"core": {"rsi_oversold_threshold": 20}}],
            }
        )


def test_single_axis_is_rejected() -> None:
    with pytest.raises(ValueError, match="至少 2 轴"):
        AttributionSettings.to_usable(
            {
                "steps": ["enumerate"],
                "matrix": {"core": {"rsi_oversold_threshold": [20, 25, 30]}},
            }
        )
