"""涨跌停贴板判断（is_at_limit_up / is_at_limit_down）。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run

from core.modules.market_profile import MarketRulesProxy
from core.modules.market_profile.core.services.amplitude_limit_service import (
    AmplitudeLimitService,
)


@pytest.fixture
def china_rules():
    return MarketRulesProxy(default_market="china_a_stock").current


@pytest.fixture
def hk_rules():
    return MarketRulesProxy(default_market="hong_kong").current


class TestAmplitudeLimitServiceTouch:
    def test_eps_half_tick(self):
        assert AmplitudeLimitService.limit_touch_eps(2) == pytest.approx(0.005)

    def test_service_at_limit_up(self):
        assert AmplitudeLimitService.is_at_limit_up(
            11.0, 11.0, ratio=0.1, price_decimals=2
        )
        assert not AmplitudeLimitService.is_at_limit_up(
            10.9, 11.0, ratio=0.1, price_decimals=2
        )

    def test_service_ratio_zero_never_at_limit(self):
        assert not AmplitudeLimitService.is_at_limit_up(
            10.0, 10.0, ratio=0.0, price_decimals=2
        )
        assert not AmplitudeLimitService.is_at_limit_down(
            10.0, 10.0, ratio=0.0, price_decimals=2
        )


class TestIsAtLimitUpDown:
    def test_main_board_limit_up(self, china_rules):
        # prev=10 → limit_up=11
        assert china_rules.is_at_limit_up(11.0, 10.0, "600000.SH") is True
        assert china_rules.is_at_limit_up(10.99, 10.0, "600000.SH") is False
        assert china_rules.is_at_limit_up(10.5, 10.0, "600000.SH") is False

    def test_main_board_limit_down(self, china_rules):
        # prev=10 → limit_down=9
        assert china_rules.is_at_limit_down(9.0, 10.0, "600000.SH") is True
        assert china_rules.is_at_limit_down(9.01, 10.0, "600000.SH") is False
        assert china_rules.is_at_limit_down(9.5, 10.0, "600000.SH") is False

    def test_star_board_wider_band(self, china_rules):
        # 科创板 ±20%：prev=10 → up=12, down=8
        assert china_rules.is_at_limit_up(12.0, 10.0, "688001.SH") is True
        assert china_rules.is_at_limit_up(11.0, 10.0, "688001.SH") is False
        assert china_rules.is_at_limit_down(8.0, 10.0, "688001.SH") is True

    def test_st_status_tags_narrow_band(self, china_rules):
        # ST ±5%：prev=10 → up=10.5, down=9.5
        assert china_rules.is_at_limit_up(
            10.5, 10.0, "600000.SH", status_tags=["st"]
        ) is True
        assert china_rules.is_at_limit_up(11.0, 10.0, "600000.SH", status_tags=["st"]) is True
        assert china_rules.is_at_limit_up(
            10.4, 10.0, "600000.SH", status_tags=["st"]
        ) is False
        assert china_rules.is_at_limit_down(
            9.5, 10.0, "600000.SH", status_tags=["st"]
        ) is True

    def test_invalid_inputs_return_false(self, china_rules):
        assert china_rules.is_at_limit_up(11.0, 0.0, "600000.SH") is False
        assert china_rules.is_at_limit_up(0.0, 10.0, "600000.SH") is False
        assert china_rules.is_at_limit_down(9.0, -1.0, "600000.SH") is False

    def test_no_amplitude_market_always_false(self, hk_rules):
        assert hk_rules.is_at_limit_up(100.0, 10.0, "00700.HK") is False
        assert hk_rules.is_at_limit_down(0.01, 10.0, "00700.HK") is False
