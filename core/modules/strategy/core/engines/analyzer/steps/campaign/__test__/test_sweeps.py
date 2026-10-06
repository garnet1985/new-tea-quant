"""参数扫描：sweeps + sensitivity_rank。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import (
    SummarizeStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize.bridge import (
    upstream_bridge,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize.joint_sweeps import (
    build_joint_heatmaps,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize.sweeps import (
    build_parameter_sweeps,
)

pytestmark = pytest.mark.force_run


def test_upstream_bridge_price_mentions_enum_and_denoised():
    gathered = {
        "rows": [
            {
                "version_id": "1",
                "status": "hit",
                "overlay": {},
                "knobs": {},
                "layers": {
                    "enumerate": {"total_opportunities": 120},
                    "price_factor": {
                        "avg_roi": 0.04,
                        "total_completed_investments": 40,
                    },
                },
            }
        ]
    }
    text = upstream_bridge(gathered, layer="price_factor")
    assert "120" in text
    assert "40" in text


def test_build_parameter_sweeps_ranks_by_span():
    gathered = {
        "rows": [
            {
                "version_id": "1",
                "status": "hit",
                "overlay": {},
                "knobs": {
                    "portfolio.allocation.max_portfolio_size": 10,
                    "core.rsi_oversold": 20,
                },
                "layers": {
                    "portfolio": {
                        "total_return": 0.10,
                        "max_drawdown": 0.20,
                        "win_rate": 0.5,
                        "capital_utilization_ratio_pct": 60.0,
                    }
                },
            },
            {
                "version_id": "1-1",
                "status": "hit",
                "overlay": {"portfolio": {"allocation": {"max_portfolio_size": 20}}},
                "knobs": {
                    "portfolio.allocation.max_portfolio_size": 20,
                    "core.rsi_oversold": 20,
                },
                "layers": {
                    "portfolio": {
                        "total_return": 0.12,
                        "max_drawdown": 0.22,
                        "win_rate": 0.52,
                        "capital_utilization_ratio_pct": 70.0,
                    }
                },
            },
            {
                "version_id": "1-2",
                "status": "hit",
                "overlay": {"core": {"rsi_oversold": 30}},
                "knobs": {
                    "portfolio.allocation.max_portfolio_size": 10,
                    "core.rsi_oversold": 30,
                },
                "layers": {
                    "portfolio": {
                        "total_return": 0.02,
                        "max_drawdown": 0.15,
                        "win_rate": 0.4,
                        "capital_utilization_ratio_pct": 40.0,
                    }
                },
            },
        ]
    }
    pack = build_parameter_sweeps(
        gathered,
        layer="portfolio",
        primary_outcome="total_return",
        extra_outcomes=("max_drawdown",),
        knob_prefixes=("portfolio.", "core."),
    )
    assert len(pack["sweeps"]) == 2
    assert pack["sensitivity_rank"][0]["knob"] == "core.rsi_oversold"
    assert pack["sensitivity_rank"][0]["span"] == 0.08


def test_portfolio_summarize_emits_sweeps():
    attributed = {
        "status": "ok",
        "n": 2,
        "varying_knobs": ["portfolio.allocation.max_portfolio_size"],
        "layers": {},
        "contributions": {
            "presence": {"status": "skipped", "items": []},
            "sensitivity": {"status": "ok", "items": []},
        },
    }
    gathered = {
        "rows": [
            {
                "version_id": "1",
                "status": "hit",
                "overlay": {},
                "knobs": {"portfolio.allocation.max_portfolio_size": 10},
                "layers": {
                    "portfolio": {
                        "total_return": 0.1,
                        "max_drawdown": 0.2,
                        "win_rate": 0.5,
                        "capital_utilization_ratio_pct": 55.0,
                    }
                },
            },
            {
                "version_id": "1-1",
                "status": "hit",
                "overlay": {"portfolio": {"allocation": {"max_portfolio_size": 20}}},
                "knobs": {"portfolio.allocation.max_portfolio_size": 20},
                "layers": {
                    "portfolio": {
                        "total_return": 0.15,
                        "max_drawdown": 0.25,
                        "win_rate": 0.55,
                        "capital_utilization_ratio_pct": 70.0,
                    }
                },
            },
        ]
    }
    out = SummarizeStep.run(
        attributed, layer="portfolio", folder=None, gathered=gathered
    )
    assert out["analysis_mode"] == "oaat"
    assert out["sweep_primary_outcome"] == "total_return"
    assert len(out["sweeps"]) == 1
    assert out["sweeps"][0]["best"]["value"] == 20
    assert out["sensitivity_rank"][0]["impact"] in {"小", "中", "大"}
    assert "资金分配" in out["scope_note"]


def test_portfolio_summarize_does_not_rank_strategy_knobs():
    attributed = {
        "status": "ok",
        "n": 3,
        "varying_knobs": [
            "portfolio.allocation.max_portfolio_size",
            "core.rsi_oversold_threshold",
        ],
        "layers": {},
        "contributions": {},
    }
    gathered = {
        "rows": [
            {
                "version_id": "1",
                "status": "hit",
                "overlay": {},
                "knobs": {
                    "portfolio.allocation.max_portfolio_size": 10,
                    "core.rsi_oversold_threshold": 20,
                    "goal.stop_loss": -0.1,
                },
                "layers": {"portfolio": {"total_return": 0.10, "max_drawdown": 0.2}},
            },
            {
                "version_id": "1-1",
                "status": "hit",
                "overlay": {"portfolio": {"allocation": {"max_portfolio_size": 4}}},
                "knobs": {
                    "portfolio.allocation.max_portfolio_size": 4,
                    "core.rsi_oversold_threshold": 20,
                    "goal.stop_loss": -0.1,
                },
                "layers": {"portfolio": {"total_return": 0.04, "max_drawdown": 0.1}},
            },
            {
                "version_id": "1-2",
                "status": "hit",
                "overlay": {"core": {"rsi_oversold_threshold": 35}},
                "knobs": {
                    "portfolio.allocation.max_portfolio_size": 10,
                    "core.rsi_oversold_threshold": 35,
                    "goal.stop_loss": -0.1,
                },
                "layers": {"portfolio": {"total_return": 0.40, "max_drawdown": 0.3}},
            },
        ]
    }
    out = SummarizeStep.run(
        attributed, layer="portfolio", folder=None, gathered=gathered
    )
    knobs = [item["knob"] for item in out["sensitivity_rank"]]
    assert knobs == ["portfolio.allocation.max_portfolio_size"]
    assert "资金分配" in out["scope_note"]
    assert "不在本层排名" in out["scope_note"]


def test_joint_heatmap_from_multi_path_overlays():
    gathered = {
        "rows": [
            {
                "version_id": "1",
                "status": "hit",
                "overlay": {},
                "knobs": {"goal.stop_loss": -0.2, "goal.take_profit": 0.2},
                "layers": {"price_factor": {"avg_roi": 0.05}},
            },
            {
                "version_id": "1-1",
                "status": "hit",
                "overlay": {
                    "goal": {
                        "stop_loss": {"stages": [{"ratio": -0.1}]},
                        "take_profit": {"stages": [{"ratio": 0.1}]},
                    }
                },
                "knobs": {"goal.stop_loss": -0.1, "goal.take_profit": 0.1},
                "layers": {"price_factor": {"avg_roi": 0.03}},
            },
            {
                "version_id": "1-2",
                "status": "hit",
                "overlay": {
                    "goal": {
                        "stop_loss": {"stages": [{"ratio": -0.1}]},
                        "take_profit": {"stages": [{"ratio": 0.2}]},
                    }
                },
                "knobs": {"goal.stop_loss": -0.1, "goal.take_profit": 0.2},
                "layers": {"price_factor": {"avg_roi": 0.06}},
            },
            {
                "version_id": "1-3",
                "status": "hit",
                "overlay": {
                    "goal": {
                        "stop_loss": {"stages": [{"ratio": -0.2}]},
                        "take_profit": {"stages": [{"ratio": 0.1}]},
                    }
                },
                "knobs": {"goal.stop_loss": -0.2, "goal.take_profit": 0.1},
                "layers": {"price_factor": {"avg_roi": 0.04}},
            },
            {
                "version_id": "1-4",
                "status": "hit",
                "overlay": {
                    "goal": {
                        "stop_loss": {"stages": [{"ratio": -0.2}]},
                        "take_profit": {"stages": [{"ratio": 0.2}]},
                    }
                },
                "knobs": {"goal.stop_loss": -0.2, "goal.take_profit": 0.2},
                "layers": {"price_factor": {"avg_roi": 0.07}},
            },
        ]
    }
    joints = build_joint_heatmaps(
        gathered, layer="price_factor", primary_outcome="avg_roi"
    )
    assert len(joints) == 1
    assert joints[0]["knobs"] == ["goal.stop_loss", "goal.take_profit"]
    assert joints[0]["best"]["metric"] == 0.07
    grid = joints[0]["grid"]
    assert len(grid["row_labels"]) == 2
    assert len(grid["col_labels"]) == 2
