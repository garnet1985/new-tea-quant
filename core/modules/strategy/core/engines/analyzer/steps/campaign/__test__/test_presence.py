"""overlay None = 关：指纹换号；effective 上区分贡献度 / 敏感度。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.attribute import (
    AttributeStep,
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
from core.modules.strategy.core.engines.analyzer.steps.campaign.summarize import (
    SummarizeStep,
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


def test_classify_presence_and_sensitivity() -> None:
    sl_on = {"stages": [{"ratio": -0.2, "close_invest": True}]}
    rows = [
        {
            "knobs": {
                "core.max_pe_percentile": 30,
                "goal.stop_loss": sl_on,
            }
        },
        {
            "knobs": {
                "core.max_pe_percentile": 20,
                "goal.stop_loss": sl_on,
            }
        },
        {
            "knobs": {
                "core.max_pe_percentile": None,
                "goal.stop_loss": sl_on,
            }
        },
        {
            "knobs": {
                "core.max_pe_percentile": 30,
                "goal.stop_loss": None,
            }
        },
    ]
    contrasts = KnobContrasts.classify(rows)
    assert contrasts["presence"] == [
        "core.max_pe_percentile",
        "goal.stop_loss",
    ]
    assert contrasts["sensitivity"] == ["core.max_pe_percentile"]


def _row(vid: str, knobs: dict, *, ret: float, opp: float) -> dict:
    return {
        "status": "hit",
        "version_id": vid,
        "knobs": knobs,
        "layers": {
            "enumerate": {"total_opportunities": opp},
            "price_factor": {"win_rate": 0.5, "avg_roi": 0.01},
            "portfolio": {"total_return": ret, "max_drawdown": -0.1},
        },
    }


def test_attribute_two_chapters() -> None:
    sl_on = {"stages": [{"ratio": -0.2, "close_invest": True}]}
    gathered = {
        "rows": [
            _row("1", {"core.max_pe_percentile": 30, "goal.stop_loss": sl_on}, ret=0.10, opp=100),
            _row("2", {"core.max_pe_percentile": 20, "goal.stop_loss": sl_on}, ret=0.12, opp=80),
            _row("3", {"core.max_pe_percentile": None, "goal.stop_loss": sl_on}, ret=0.04, opp=200),
            _row("4", {"core.max_pe_percentile": 30, "goal.stop_loss": None}, ret=0.02, opp=100),
        ]
    }
    out = AttributeStep.run(gathered)
    presence = out["contributions"]["presence"]
    sensitivity = out["contributions"]["sensitivity"]
    assert "core.max_pe_percentile" in out["presence_paths"]
    assert "goal.stop_loss" in out["presence_paths"]
    assert "core.max_pe_percentile" in out["sensitivity_paths"]
    assert "goal.stop_loss" not in out["sensitivity_paths"]

    pe_presence = [
        item
        for item in presence["items"]
        if item.get("kind") == "one_at_a_time"
        and item.get("knob") == "core.max_pe_percentile"
    ]
    assert pe_presence
    assert all(item.get("from") is None for item in pe_presence)
    assert {item.get("baseline_version_id") for item in pe_presence} == {"3"}

    sl_presence = [
        item
        for item in presence["items"]
        if item.get("kind") == "one_at_a_time" and item.get("knob") == "goal.stop_loss"
    ]
    assert sl_presence
    assert sl_presence[0].get("baseline_version_id") == "4"

    pe_sens = [
        item
        for item in sensitivity.get("items") or []
        if item.get("kind") == "one_at_a_time"
        and item.get("knob") == "core.max_pe_percentile"
    ]
    assert pe_sens
    assert sensitivity.get("baseline", {}).get("version_id") == "1"
    assert all(item.get("from") == 30 for item in pe_sens)
    assert all(item.get("to") is not None for item in pe_sens)


def test_overlay_none_is_legal() -> None:
    snapshot = _snapshot()
    cfg = AttributionConfig.to_usable(
        {
            "overlays": [
                {"core": {"rsi_oversold_threshold": 20}},
                {"core": {"max_pe_percentile": None}},
                {"goal": {"stop_loss": None}},
            ],
        }
    )
    assert len(cfg.overlays) == 3
    cells = AttributionPlan.expand(snapshot, cfg)
    assert len(cells) == 4
    assert cells[0].overlay == {}
    pe_off = cells[2]
    sl_off = cells[3]
    assert KnobContrasts.value_at(pe_off.effective.raw_settings, "core.max_pe_percentile") is None
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
    assert tasks[0].steps == (SimulateKind.PORTFOLIO,)
    assert cfg.parameter_mode == "overlays"


def test_overlay_snapshot_baseline_makes_oat() -> None:
    sl_on = {"stages": [{"ratio": -0.2, "close_invest": True}]}
    gathered = {
        "rows": [
            _row(
                "21",
                {
                    "core.rsi_oversold_threshold": 20,
                    "core.max_pe_percentile": 30,
                    "goal.stop_loss": sl_on,
                },
                ret=0.07,
                opp=18,
            ),
            _row(
                "22",
                {
                    "core.rsi_oversold_threshold": 25,
                    "core.max_pe_percentile": 30,
                    "goal.stop_loss": sl_on,
                },
                ret=0.50,
                opp=78,
            ),
            _row(
                "26",
                {
                    "core.rsi_oversold_threshold": 20,
                    "core.max_pe_percentile": None,
                    "goal.stop_loss": sl_on,
                },
                ret=0.20,
                opp=32,
            ),
            _row(
                "31",
                {
                    "core.rsi_oversold_threshold": 20,
                    "core.max_pe_percentile": 30,
                    "goal.stop_loss": None,
                },
                ret=0.17,
                opp=16,
            ),
        ]
    }
    out = AttributeStep.run(gathered)
    presence = (out.get("contributions") or {}).get("presence") or {}
    oat = {
        item.get("knob")
        for item in presence.get("items") or []
        if item.get("kind") == "one_at_a_time"
    }
    assert "core.max_pe_percentile" in oat
    assert "goal.stop_loss" in oat
    headline = str(SummarizeStep.run(out).get("headline") or "")
    assert "没有变化" not in headline


def test_price_layer_dedupes_portfolio_only_overlay() -> None:
    """spa 不看 portfolio：只改组合容量的回测与基准指纹相同，贡献度不应重复。"""
    from core.modules.strategy.core.engines.analyzer.steps.campaign.attribute import (
        PriceAttributeStep,
    )

    sl_on = {"stages": [{"ratio": -0.2, "close_invest": True}]}
    gathered = {
        "rows": [
            _row(
                "1",
                {
                    "core.max_pe_percentile": 30,
                    "goal.stop_loss": sl_on,
                    "portfolio.allocation.max_portfolio_size": 10,
                },
                ret=0.10,
                opp=18,
            ),
            _row(
                "1-2",
                {
                    "core.max_pe_percentile": None,
                    "goal.stop_loss": sl_on,
                    "portfolio.allocation.max_portfolio_size": 10,
                },
                ret=0.04,
                opp=32,
            ),
            _row(
                "1-4",
                {
                    "core.max_pe_percentile": 30,
                    "goal.stop_loss": sl_on,
                    "portfolio.allocation.max_portfolio_size": 20,
                },
                ret=0.10,
                opp=18,
            ),
        ]
    }
    out = PriceAttributeStep.run(gathered)
    pe_oat = [
        item
        for item in (out["contributions"]["presence"].get("items") or [])
        if item.get("kind") == "one_at_a_time"
        and item.get("knob") == "core.max_pe_percentile"
    ]
    assert len(pe_oat) == 1
    assert pe_oat[0].get("version_id") == "1"


def test_enumerate_layer_drops_portfolio_knobs() -> None:
    from core.modules.strategy.core.engines.analyzer.steps.campaign.attribute import (
        EnumerateAttributeStep,
    )

    assert not EnumerateAttributeStep.accepts_knob(
        "portfolio.allocation.max_portfolio_size"
    )
    assert EnumerateAttributeStep.accepts_knob("core.rsi_oversold_threshold")
    assert EnumerateAttributeStep.accepts_knob("goal.stop_loss")

    gathered = {
        "rows": [
            _row(
                "1",
                {
                    "core.max_pe_percentile": 30,
                    "portfolio.allocation.max_portfolio_size": 10,
                },
                ret=0.10,
                opp=18,
            ),
            _row(
                "2",
                {
                    "core.max_pe_percentile": None,
                    "portfolio.allocation.max_portfolio_size": 20,
                },
                ret=0.04,
                opp=32,
            ),
        ]
    }
    out = EnumerateAttributeStep.run(gathered)
    assert "core.max_pe_percentile" in out["presence_paths"]
    assert "portfolio.allocation.max_portfolio_size" not in out["presence_paths"]
    assert "portfolio.allocation.max_portfolio_size" not in out["sensitivity_paths"]
    assert "portfolio.allocation.max_portfolio_size" not in (out.get("varying_knobs") or [])
    assert set(out.get("layers") or {}) == {"enumerate"}
    deltas = []
    for item in (out["contributions"]["presence"].get("items") or []):
        deltas.extend(item.get("deltas") or [])
    assert deltas
    assert all(part.get("layer") == "enumerate" for part in deltas)


def test_attribution_settings_drops_fill_missing() -> None:
    cfg = AttributionConfig.to_usable(
        {
            "fill_missing": True,
            "overlays": [{"core": {"rsi_oversold_threshold": 20}}],
            "rolling": {
                "windows": [{"start": "20230101", "end": "20231231"}],
                "fill_missing": False,
            },
        }
    )
    dumped = cfg.to_dict()
    assert "fill_missing" not in dumped
    assert "fill_missing" not in (dumped.get("rolling") or {})
    assert "steps" not in dumped
