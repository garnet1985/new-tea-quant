"""goal.stock_status_risk_management 解析与校验。"""
import pytest

from core.modules.strategy.engines.shared.data_classes.strategy_settings.stock_status_risk_settings import (
    StockStatusRiskManagementSettings,
)


def test_default_empty_rules():
    s = StockStatusRiskManagementSettings.from_goal_block(None)
    assert s.rules == ()
    assert s.delisted_exit_price == "last_tradable_close"


def test_list_form_rules_only():
    s = StockStatusRiskManagementSettings.from_goal_block(
        [{"name": "st", "close_invest": True}]
    )
    assert len(s.rules) == 1
    assert s.rules[0].name == "st"
    assert s.rules[0].close_invest is True


def test_reject_delisted_in_rules():
    with pytest.raises(ValueError, match="delisted"):
        StockStatusRiskManagementSettings.from_goal_block(
            [{"name": "delisted"}]
        )


def test_dict_form_with_exit_price():
    s = StockStatusRiskManagementSettings.from_goal_block(
        {
            "rules": [{"name": "star_st", "close_invest": True}],
            "delisted_exit_price": "same_bar_close",
        }
    )
    assert s.rules[0].name == "star_st"
    assert s.delisted_exit_price == "same_bar_close"
