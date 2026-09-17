"""HfqRoi / 同股市值：合法价、缺价、送转后因子已折进 hfq。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.hfq_roi import HfqRoi


def test_hfq_roi_is_current_over_entry_minus_one() -> None:
    assert HfqRoi.ratio(10.0, 12.0) == pytest.approx(0.2)
    assert HfqRoi.ratio(100.0, 100.0) == 0.0
    assert HfqRoi.ratio(10.0, 8.0) == pytest.approx(-0.2)


def test_hfq_roi_rejects_non_positive_or_bad_prices() -> None:
    assert HfqRoi.ratio(0.0, 12.0) == 0.0
    assert HfqRoi.ratio(-10.0, 12.0) == 0.0
    assert HfqRoi.ratio(10.0, 0.0) == 0.0
    assert HfqRoi.ratio(None, 12.0) == 0.0
    assert HfqRoi.ratio(10.0, float("nan")) == 0.0


def test_split_leaves_hfq_roi_flat_when_factor_absorbs_it() -> None:
    """10 送 10：冻结股数不变，hfq 不跌，ROI 为 0；禁止用 raw 腰斩当收益。"""
    assert HfqRoi.ratio(10.0, 10.0) == 0.0
    assert HfqRoi.cash_profit(100, 10.0, 0.0) == 0.0
    assert HfqRoi.mark_value(100, 10.0, 0.0) == 1000.0


def test_cash_profit_and_mark_value_follow_roi() -> None:
    roi = HfqRoi.ratio(10.0, 12.0)
    assert HfqRoi.cash_profit(100, 10.0, roi) == pytest.approx(200.0)
    assert HfqRoi.mark_value(100, 10.0, roi) == pytest.approx(1200.0)


def test_hfq_target_hit_uses_price_not_floaty_roi() -> None:
    assert HfqRoi.target_price(10.0, 0.2) == pytest.approx(12.0)
    assert HfqRoi.target_price(10.0, -0.2) == pytest.approx(8.0)
    assert HfqRoi.is_target_hit(10.0, 12.0, 0.2) is True
    assert HfqRoi.is_target_hit(10.0, 11.9, 0.2) is False
    assert HfqRoi.is_target_hit(10.0, 8.0, -0.2) is True
    assert HfqRoi.is_target_hit(10.0, 8.01, -0.2) is False
    assert HfqRoi.is_target_hit(10.0, 10.0, 0.0) is True
    assert HfqRoi.is_target_hit(10.0, 10.01, 0.0) is False
