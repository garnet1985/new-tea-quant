"""matrix 是各轴笛卡尔积；旧的 list 写法要改成 overlays。"""
from __future__ import annotations

from typing import Any

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.attribute import (
    AttributeStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.cells import (
    AttributionTask,
    CellExpander,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.config import (
    AttributionSettings,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.contrasts import (
    KnobContrasts,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.execute import (
    ExecuteStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.grid import (
    SettingsMatrix,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import (
    SummarizeStep,
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


def _grid_row(vid: str, rsi: float, pe: Any, ret: float) -> dict:
    return {
        "status": "hit",
        "version_id": vid,
        "knobs": {
            "core.rsi_oversold_threshold": rsi,
            "core.max_pe_percentile": pe,
        },
        "layers": {
            "enumerate": {"total_opportunities": 10},
            "price_factor": {"win_rate": 0.5, "avg_roi": 0.01},
            "portfolio": {"total_return": ret, "max_drawdown": -0.1},
        },
    }


def test_matrix_rectangle_keeps_off_axis() -> None:
    gathered = {
        "rows": [
            _grid_row("21", 20, 30, 0.07),
            _grid_row("26", 20, None, 0.20),
            _grid_row("22", 25, 30, 0.50),
            _grid_row("32", 25, None, 0.60),
        ]
    }
    out = AttributeStep.run(gathered)
    interactions = (out.get("contributions") or {}).get("sensitivity", {}).get(
        "interactions"
    ) or {}
    assert interactions.get("status") == "ok"
    grid = (interactions.get("grids") or [None])[0]
    assert grid is not None
    assert int(grid.get("n_cells") or 0) == 4
    best = grid.get("best") or {}
    assert best.get("total_return") == pytest.approx(0.60)
    assert best.get("row_value") in (25, 25.0) or best.get("col_value") in (25, 25.0)
    headline = SummarizeStep.run(out).get("headline") or ""
    assert "×" in headline
    assert "60.0%" in headline


def test_overlays_and_matrix_coexist() -> None:
    cfg = AttributionSettings.to_usable(
        {
            "steps": ["enumerate"],
            "overlays": [{"core": {"rsi_oversold_threshold": 25}}],
            "matrix": {
                "core": {
                    "rsi_oversold_threshold": [20, 25],
                    "max_pe_percentile": [30, None],
                }
            },
        }
    )
    assert cfg.parameter_mode == "overlays+matrix"
    dumped = cfg.to_dict()
    assert dumped.get("overlays")
    assert dumped.get("matrix")
    plan = CellExpander.plan(_snapshot(), cfg)
    assert len(plan.overlays) == 1
    assert len(plan.matrix) == 4
    unique = ExecuteStep.unique_tasks(
        AttributionTask.from_cells(plan.execute_source_cells(), cfg)
    )
    assert len(unique) == 4


def test_versions_exclusive_with_overlays() -> None:
    with pytest.raises(ValueError, match="versions"):
        AttributionSettings.to_usable(
            {
                "steps": ["enumerate"],
                "versions": [1],
                "overlays": [{"core": {"rsi_oversold_threshold": 20}}],
            }
        )
