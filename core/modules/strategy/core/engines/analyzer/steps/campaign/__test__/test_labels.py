"""战役数字格式：财报 yoy 已经是百分数。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.labels import CampaignLabels

pytestmark = pytest.mark.force_run


def test_format_number_yoy_already_percent() -> None:
    key = "stock.finance.quarterly.netprofit_yoy"
    assert CampaignLabels.format_number(key, 16.468) == "16.5%"
    assert CampaignLabels.format_number(key, 43.1) == "43.1%"
    assert CampaignLabels.format_number("min_netprofit_yoy", 0) == "0.0%"


def test_format_number_ratio_still_scales() -> None:
    assert CampaignLabels.format_number("total_return", 0.197) == "+19.7%"
    assert CampaignLabels.format_number("stop_loss", -0.2) == "-20.0%"


def test_opportunity_selection_knob_label() -> None:
    assert CampaignLabels.knob_label("portfolio.allocation.opportunity_selection") == "选仓排序"
    assert CampaignLabels.format_knob("opportunity_selection", []) == "到达顺序"
    assert (
        CampaignLabels.format_knob(
            "opportunity_selection",
            [{"rsi": "ASC"}, {"pe_percentile": "asc"}],
        )
        == "rsi ASC，pe_percentile ASC"
    )
    assert (
        CampaignLabels.format_knob(
            "opportunity_selection",
            [{"rsi": -70}, {"pe_percentile": -30}],
        )
        == "rsi×-70，pe_percentile×-30"
    )


def test_knob_label_keeps_user_core_keys() -> None:
    assert CampaignLabels.knob_label("core.rsi_oversold_threshold") == "rsi_oversold_threshold"
    assert CampaignLabels.knob_label("core.max_pe_percentile") == "max_pe_percentile"
    assert CampaignLabels.knob_label("rsi_oversold_threshold") == "rsi_oversold_threshold"


def test_knob_label_translates_system_keys() -> None:
    assert CampaignLabels.knob_label("max_portfolio_size") == "组合容量"
    assert CampaignLabels.knob_label("portfolio.allocation.max_portfolio_size") == "组合容量"
    assert CampaignLabels.knob_label("goal.stop_loss") == "止损"
    assert CampaignLabels.knob_label("goal.take_profit") == "止盈"


def test_format_knob_enum_values() -> None:
    assert CampaignLabels.format_knob("mode", "equal_capital") == "等权资金"
    assert CampaignLabels.format_knob("goal.stop_loss", None) == "未使用"
