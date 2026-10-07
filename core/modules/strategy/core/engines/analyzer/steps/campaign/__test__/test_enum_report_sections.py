"""枚举归因报告：gather 扩宽指标 + summarize 五节。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.gather.base import (
    compact_summary,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.gather.enum_exits import (
    after_take_profit_probe,
    baseline_exit_diagnosis,
    ratios_from_results,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import (
    SummarizeStep,
)
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import (
    enumerate as enumerate_summarize,
)
from core.modules.strategy.core.enums import SimulateKind

pytestmark = pytest.mark.force_run


def test_compact_summary_enum_keys_and_top_bucket():
    summary = {
        "total_opportunities": 18,
        "trigger_stocks": 15,
        "trigger_ratio": 0.05,
        "avg_per_stock": 1.2,
        "completed_ratio": 1.0,
        "cv": 0.65,
        "mean_gap": 35.0,
        "dispersion_conclusion": "中等聚集",
        "opportunity_count_max": 2,
        "opportunity_count_stock_ratios": [95.0, 5.0],
    }
    out = compact_summary(SimulateKind.ENUMERATE, summary)
    assert out["total_opportunities"] == 18
    assert out["trigger_stocks"] == 15
    assert out["cv"] == 0.65
    # 机会最多的那只票 2 / 全部 18
    assert out["top_bucket_ratio"] == pytest.approx(0.1111)


def test_ratios_from_results():
    rows = [
        {"exit_reason": "take_profit", "holding_days": 10},
        {"exit_reason": "take_profit", "holding_days": 12},
        {"exit_reason": "stop_loss", "holding_days": 3},
        {"exit_reason": "simulate_end", "holding_days": 40},
    ]
    out = ratios_from_results(rows)
    assert out["n_exits"] == 4
    assert out["take_profit_ratio"] == pytest.approx(0.5)
    assert out["stop_loss_ratio"] == pytest.approx(0.25)
    assert out["expire_ratio"] == pytest.approx(0.25)
    assert out["avg_holding_days_stop_loss"] == pytest.approx(3.0)


def test_after_take_profit_unavailable_for_single_full_close(tmp_path: Path):
    settings = {
        "goal": {
            "take_profit": {
                "stages": [{"ratio": 0.2, "close_invest": True}],
            }
        }
    }
    out = after_take_profit_probe(tmp_path, "1", settings)
    assert out["available"] is False
    assert "一档全平" in out["reason"]


def test_after_take_profit_available_for_multi_stage(tmp_path: Path):
    settings = {
        "goal": {
            "take_profit": {
                "stages": [
                    {"ratio": 0.1, "close_invest": False, "exit_ratio": 0.5},
                    {"ratio": 0.2, "close_invest": True},
                ],
            }
        }
    }
    # 空标的：有产物，但没有多段命中
    out = after_take_profit_probe(tmp_path, "1", settings)
    assert out["available"] is True


def test_baseline_exit_diagnosis_from_entities(tmp_path: Path):
    enum_dir = tmp_path / "results" / "simulations" / "1" / "enum" / "entities"
    enum_dir.mkdir(parents=True)
    (enum_dir / "AAA.json").write_text(
        json.dumps(
            {
                "entity_id": "AAA",
                "results": [
                    {
                        "entity_id": "AAA",
                        "stock_name": "票A",
                        "exit_reason": "stop_loss",
                        "trigger_date": "20240115",
                        "holding_days": 2,
                        "completed_goals": [],
                    },
                    {
                        "entity_id": "AAA",
                        "stock_name": "票A",
                        "exit_reason": "stop_loss",
                        "trigger_date": "20240210",
                        "holding_days": 3,
                        "completed_goals": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (enum_dir / "BBB.json").write_text(
        json.dumps(
            {
                "entity_id": "BBB",
                "results": [
                    {
                        "entity_id": "BBB",
                        "stock_name": "票B",
                        "exit_reason": "take_profit",
                        "trigger_date": "20240120",
                        "holding_days": 8,
                        "completed_goals": [{"name": "win20%"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    # 绕过 ArtifactStore.open 对 runtime_env 的要求
    (enum_dir.parent / "runtime_env.json").write_text("{}", encoding="utf-8")
    diagnosis = baseline_exit_diagnosis(tmp_path, "1", top_n=3)
    assert diagnosis["n"] == 3
    assert diagnosis["exit_counts"]["stop_loss"] == 2
    assert diagnosis["high_stop_loss_stocks"][0]["entity_id"] == "AAA"


def test_enumerate_summarize_sections_value_ladders():
    """非交叉：每旋钮一块——最多/最少/趋势 + 相对当前配置对照表。"""
    attributed = {
        "status": "ok",
        "n": 4,
        "varying_knobs": [
            "core.max_pe_percentile",
            "core.rsi_oversold",
            "goal.stop_loss",
        ],
        "layers": {},
    }
    stop_on = {"stages": [{"ratio": -0.2, "close_invest": True}]}
    gathered = {
        "rows": [
            {
                "version_id": "1",
                "status": "hit",
                "overlay": {},
                "knobs": {
                    "core.max_pe_percentile": 30,
                    "core.rsi_oversold": 20,
                    "goal.stop_loss": stop_on,
                },
                "layers": {
                    "enum": {
                        "total_opportunities": 18,
                        "trigger_ratio": 0.05,
                        "top_bucket_ratio": 0.4,
                        "cv": 0.6,
                        "stop_loss_ratio": 0.25,
                        "take_profit_ratio": 0.5,
                    }
                },
            },
            {
                "version_id": "1-1",
                "status": "hit",
                "overlay": {"core": {"max_pe_percentile": None}},
                "knobs": {
                    "core.max_pe_percentile": None,
                    "core.rsi_oversold": 20,
                    "goal.stop_loss": stop_on,
                },
                "layers": {
                    "enum": {
                        "total_opportunities": 32,
                        "trigger_ratio": 0.08,
                        "top_bucket_ratio": 0.35,
                        "cv": 0.55,
                        "stop_loss_ratio": 0.22,
                        "take_profit_ratio": 0.48,
                    }
                },
            },
            {
                "version_id": "1-2",
                "status": "hit",
                "overlay": {"core": {"rsi_oversold": 25}},
                "knobs": {
                    "core.max_pe_percentile": 30,
                    "core.rsi_oversold": 25,
                    "goal.stop_loss": stop_on,
                },
                "layers": {
                    "enum": {
                        "total_opportunities": 78,
                        "trigger_ratio": 0.15,
                        "top_bucket_ratio": 0.5,
                        "cv": 0.7,
                        "stop_loss_ratio": 0.3,
                        "take_profit_ratio": 0.4,
                    }
                },
            },
            {
                "version_id": "1-3",
                "status": "hit",
                "overlay": {"goal": {"stop_loss": None}},
                "knobs": {
                    "core.max_pe_percentile": 30,
                    "core.rsi_oversold": 20,
                    "goal.stop_loss": None,
                },
                "layers": {
                    "enum": {
                        "total_opportunities": 18,
                        "trigger_ratio": 0.05,
                        "top_bucket_ratio": 0.4,
                        "cv": 0.6,
                        "stop_loss_ratio": 0.0,
                        "take_profit_ratio": 0.55,
                    }
                },
            },
        ]
    }
    out = SummarizeStep.run(
        attributed, layer="enum", folder=None, gathered=gathered
    )
    assert out["scope_note"]
    sections = out["sections"]
    opp = sections["opportunity"]
    effects = opp.get("effects") or []
    pe = next(item for item in effects if item.get("knob") == "core.max_pe_percentile")
    assert "机会" in pe["title"]
    assert pe["max_line"].startswith("最好情况：")
    assert pe["min_line"].startswith("最差情况：")
    assert "未使用" in pe["max_line"]
    assert "30" in pe["min_line"]
    # 结论不重复表格里的具体指标数字
    assert "32" not in pe["max_line"]
    assert "18" not in pe["min_line"]
    assert pe["best"]["value"] is None
    assert pe["best"]["metric"] == 32
    assert pe["worst"]["value"] == 30
    assert any(row.get("is_baseline") for row in pe["table"])
    assert any(
        row.get("value") is None and row.get("delta_label") not in {None, "当前配置"}
        for row in pe["table"]
    )
    rsi = next(item for item in effects if item.get("knob") == "core.rsi_oversold")
    assert rsi["best"]["value"] == 25
    assert rsi["trend_line"].startswith("趋势：")
    assert "越高" in rsi["trend_line"] or "越低" in rsi["trend_line"] or "不变" in rsi["trend_line"]
    # goal 轴不得进入机会数 effects
    assert all(not str(item.get("knob") or "").startswith("goal.") for item in effects)

    exit_sec = sections["exit_quality"]
    exit_effects = exit_sec.get("effects") or []
    assert any(item.get("knob") == "goal.stop_loss" for item in exit_effects)
    # 得不到止盈后结论时不写这一节
    assert "after_take_profit" not in sections
    assert out.get("headline") in {"", None}
    assert out.get("analysis_mode") == "oaat"
    assert "单因素扫描" in (out.get("scope_note") or "")
    assert all(not str(sec.get("suggestion") or "") for sec in sections.values())
    assert "各个参数是如何影响回测找到的机会总数？" in opp["question"]
    sweeps = out.get("sweeps") or []
    assert {item["knob"] for item in sweeps} >= {
        "core.max_pe_percentile",
        "core.rsi_oversold",
        "goal.stop_loss",
    }
    rank = out.get("sensitivity_rank") or []
    assert rank
    assert rank[0]["knob"] == "core.rsi_oversold"
    assert out.get("sweep_primary_outcome") == "total_opportunities"


def test_enumerate_summarize_after_tp_gate_with_settings(tmp_path: Path, monkeypatch):
    attributed = {
        "status": "ok",
        "n": 2,
        "varying_knobs": [],
        "layers": {},
    }
    executed = {"parent_version_id": "1"}
    monkeypatch.setattr(
        enumerate_summarize,
        "_effective_settings",
        lambda folder, vid: {
            "goal": {
                "take_profit": {
                    "stages": [{"ratio": 0.2, "close_invest": True}],
                }
            }
        },
    )
    out = SummarizeStep.run(
        attributed,
        layer="enum",
        folder=tmp_path,
        gathered={
            "rows": [
                {
                    "version_id": "1",
                    "overlay": {},
                    "status": "hit",
                    "knobs": {},
                    "layers": {"enum": {"total_opportunities": 1}},
                }
            ]
        },
        executed=executed,
    )
    # 一档全平 → available=False → 整节省略
    assert "after_take_profit" not in out["sections"]