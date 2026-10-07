"""价格归因报告：ledger 指标 + summarize 三节。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.gather.price_ledger import (
    metrics_from_scan,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import (
    SummarizeStep,
)
from core.modules.strategy.core.engines.price_factor.report_manager.report_scan import (
    PriceCsvScan,
)

pytestmark = pytest.mark.force_run


def _row(*, roi: float, exit_reason: str, entity: str = "A", enter: float = 10.0):
    return SimpleNamespace(
        skip_reason="",
        exit_date="20240110",
        roi=roi,
        enter_price_hfq=enter,
        enter_price=enter,
        exit_reason=exit_reason,
    )


def test_price_ledger_metrics_from_scan():
    scan = PriceCsvScan(
        total_entities=2,
        investments_by_entity={
            "AAA": [
                _row(roi=0.2, exit_reason="take_profit"),
                _row(roi=-0.1, exit_reason="stop_loss"),
                _row(roi=0.05, exit_reason="take_profit"),
            ],
            "BBB": [
                _row(roi=0.3, exit_reason="take_profit", entity="B"),
                _row(roi=-0.05, exit_reason="expiration", entity="B"),
            ],
        },
    )
    out = metrics_from_scan(scan)
    assert out["n_completed"] == 5
    assert out["payoff_ratio"] is not None
    # 分母=盈亏绝对值之和：有赚有亏时，前5笔贡献占比 < 1，且 |出场占比| 之和 ≈ 1
    assert out["top5_trade_profit_share"] == pytest.approx(0.5714)
    assert out["take_profit_profit_share"] == pytest.approx(0.7857)
    assert out["stop_loss_profit_share"] == pytest.approx(-0.1429)
    assert out["expire_profit_share"] == pytest.approx(-0.0714)
    assert abs(out["take_profit_profit_share"]) <= 1.0 + 1e-9
    assert abs(out["top5_trade_profit_share"]) <= 1.0 + 1e-9


def test_price_summarize_sections_baseline_and_ladder():
    attributed = {
        "status": "ok",
        "n": 2,
        "varying_knobs": ["simulation.price.opportunity_merge_gap"],
        "layers": {},
    }
    gathered = {
        "rows": [
            {
                "version_id": "1",
                "status": "hit",
                "overlay": {},
                "knobs": {"simulation.price.opportunity_merge_gap": 1},
                "layers": {
                    "price_factor": {
                        "win_rate": 0.55,
                        "avg_roi": 0.04,
                        "payoff_ratio": 1.6,
                        "roi_p50": 0.03,
                        "total_profit": 120.5,
                        "total_completed_investments": 40,
                        "top5_trade_profit_share": 0.45,
                        "top5_stock_profit_share": 0.5,
                        "avg_roi_without_top5": 0.02,
                        "take_profit_profit_share": 0.8,
                        "stop_loss_profit_share": -0.2,
                        "expire_profit_share": 0.1,
                    }
                },
            },
            {
                "version_id": "1-1",
                "status": "hit",
                "overlay": {"simulation": {"price": {"opportunity_merge_gap": 3}}},
                "knobs": {"simulation.price.opportunity_merge_gap": 3},
                "layers": {
                    "price_factor": {
                        "win_rate": 0.6,
                        "avg_roi": 0.06,
                        "payoff_ratio": 1.9,
                        "roi_p50": 0.04,
                        "total_profit": 90.0,
                        "total_completed_investments": 28,
                        "top5_trade_profit_share": 0.55,
                        "top5_stock_profit_share": 0.6,
                        "avg_roi_without_top5": 0.03,
                        "take_profit_profit_share": 0.85,
                        "stop_loss_profit_share": -0.15,
                        "expire_profit_share": 0.05,
                    }
                },
            },
        ]
    }
    out = SummarizeStep.run(
        attributed, layer="price_factor", folder=None, gathered=gathered
    )
    assert out["analysis_mode"] == "oaat"
    assert "单因素扫描" in (out.get("scope_note") or "")
    sections = out["sections"]
    assert "edge" in sections
    assert "profit_concentration" in sections
    assert "exit_profit" in sections
    edge = sections["edge"]
    assert "能不能赚" in (edge.get("question") or "")
    assert any("胜率" in line for line in edge["facts"])
    assert any("总盈亏" in line for line in edge["facts"])
    effects = edge.get("effects") or []
    assert any(
        item.get("knob") == "simulation.price.opportunity_merge_gap"
        for item in effects
    )
    exit_sec = sections["exit_profit"]
    assert any("只描述" in line or "不代算" in line for line in exit_sec["facts"])
    assert out.get("headline") in {"", None}
    sweeps = out.get("sweeps") or []
    assert len(sweeps) == 1
    assert sweeps[0]["knob"] == "simulation.price.opportunity_merge_gap"
    assert sweeps[0]["primary_outcome"] == "avg_roi"
    assert len(sweeps[0]["levels"]) == 2
    rank = out.get("sensitivity_rank") or []
    assert rank and rank[0]["knob"] == "simulation.price.opportunity_merge_gap"
    assert out.get("sweep_primary_outcome") == "avg_roi"
