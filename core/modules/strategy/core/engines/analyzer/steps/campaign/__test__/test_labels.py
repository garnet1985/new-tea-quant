"""战役数字格式：财报 yoy 已经是百分数。"""
from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.labels import CampaignLabels
from core.modules.strategy.core.engines.analyzer.steps.campaign.present import (
    _shap_direction_conclusion,
)

pytestmark = pytest.mark.force_run


def test_format_number_yoy_already_percent() -> None:
    key = "stock.finance.quarterly.netprofit_yoy"
    assert CampaignLabels.format_number(key, 16.468) == "16.5%"
    assert CampaignLabels.format_number(key, 43.1) == "43.1%"
    assert CampaignLabels.format_number("min_netprofit_yoy", 0) == "0.0%"


def test_format_number_ratio_still_scales() -> None:
    assert CampaignLabels.format_number("total_return", 0.197) == "+19.7%"
    assert CampaignLabels.format_number("stop_loss", -0.2) == "-20.0%"


def test_shap_same_sign_does_not_say_lower_is_better() -> None:
    text = _shap_direction_conclusion("净利同比", 1.03, 0.30, "low_positive")
    assert "两端都倾向赚钱" in text
    assert "越低越倾向赚钱" not in text


def test_auc_warning_flags_train_test_gap() -> None:
    from core.modules.strategy.core.engines.analyzer.steps.campaign.present import (
        _auc_warning,
        _shap_dependence_conclusion,
    )

    text = _auc_warning(0.96, 0.70, {"kind": "grouped"})
    assert "过拟合" in text
    note = _shap_dependence_conclusion(
        "RSI",
        "rsi14",
        [
            {"lo": 10, "hi": 18, "mid": 14, "mean_shap": 0.04, "n": 20},
            {"lo": 18, "hi": 24, "mid": 21, "mean_shap": 0.06, "n": 20},
            {"lo": 24, "hi": 28, "mid": 26, "mean_shap": 0.01, "n": 20},
            {"lo": 28, "hi": 40, "mid": 34, "mean_shap": -0.03, "n": 20},
        ],
    )
    assert "不是单调" in note
