#!/usr/bin/env python3
"""Market Profile API 稳定性测试。

测试所有公开API的稳定性，确保接口契约不被破坏。
所有API状态为beta，可能变更。
"""

import pytest
from typing import Tuple

from core.modules.market_profile import MarketRulesProxy
from core.modules.market_profile.core.base.market_base_rules import MarketBaseRules


class TestMarketRulesProxyAPI:
    """测试 MarketRulesProxy API 稳定性"""

    def test_api_exists(self):
        """测试 MarketRulesProxy 类存在"""
        assert MarketRulesProxy is not None

    def test_constructor_with_default_market(self):
        """测试构造函数 - 默认市场"""
        proxy = MarketRulesProxy()
        assert proxy is not None
        assert isinstance(proxy, MarketRulesProxy)

    def test_constructor_with_custom_market(self):
        """测试构造函数 - 自定义市场"""
        proxy = MarketRulesProxy(default_market="us_stock")
        assert proxy is not None

    def test_mount_method(self):
        """测试 mount 方法"""
        proxy = MarketRulesProxy()
        proxy.mount("hong_kong")
        assert proxy.get_mounted_id() == "hong_kong"

    def test_mount_invalid_market(self):
        """测试 mount 方法 - 无效市场"""
        proxy = MarketRulesProxy()
        with pytest.raises(ValueError):
            proxy.mount("invalid_market")

    def test_current_property(self):
        """测试 current 属性"""
        proxy = MarketRulesProxy()
        current = proxy.current
        assert isinstance(current, MarketBaseRules)

    def test_get_market_method(self):
        """测试 get_market 方法"""
        proxy = MarketRulesProxy()
        rules = proxy.get_market("china_a_stock")
        assert isinstance(rules, MarketBaseRules)

    def test_get_market_invalid(self):
        """测试 get_market 方法 - 无效市场"""
        proxy = MarketRulesProxy()
        with pytest.raises(ValueError):
            proxy.get_market("invalid_market")

    def test_list_available_method(self):
        """测试 list_available 方法"""
        proxy = MarketRulesProxy()
        markets = proxy.list_available()
        assert isinstance(markets, list)
        assert len(markets) > 0
        assert "china_a_stock" in markets

    def test_is_available_method(self):
        """测试 is_available 方法"""
        proxy = MarketRulesProxy()
        assert proxy.is_available("china_a_stock") is True
        assert proxy.is_available("invalid_market") is False

    def test_get_mounted_id_method(self):
        """测试 get_mounted_id 方法"""
        proxy = MarketRulesProxy()
        mounted_id = proxy.get_mounted_id()
        assert isinstance(mounted_id, str)
        assert mounted_id == "china_a_stock"


class TestMarketBaseRulesAPI:
    """测试 MarketBaseRules API 稳定性"""

    @pytest.fixture
    def rules(self):
        """获取A股规则实例"""
        proxy = MarketRulesProxy()
        return proxy.current

    # ==================== 属性测试 ====================

    def test_profile_id_property(self, rules):
        """测试 profile_id 属性"""
        assert hasattr(rules, 'profile_id')
        assert isinstance(rules.profile_id, str)
        assert rules.profile_id == "china_a_stock"

    def test_name_property(self, rules):
        """测试 name 属性"""
        assert hasattr(rules, 'name')
        assert isinstance(rules.name, str)

    def test_description_property(self, rules):
        """测试 description 属性"""
        assert hasattr(rules, 'description')
        assert isinstance(rules.description, str)

    # ==================== 涨跌幅限制测试 ====================

    def test_get_limit_ratio_method(self, rules):
        """测试 get_limit_ratio 方法"""
        ratio = rules.get_limit_ratio()
        assert isinstance(ratio, float)
        assert 0.0 <= ratio <= 1.0

    def test_get_limit_ratio_for_stock_method(self, rules):
        """测试 get_limit_ratio_for_stock 方法"""
        ratio = rules.get_limit_ratio_for_stock("000001.SZ")
        assert isinstance(ratio, float)

    def test_get_limit_ratio_for_stock_with_status_tags(self, rules):
        """测试 get_limit_ratio_for_stock 方法 - 带状态标签"""
        ratio = rules.get_limit_ratio_for_stock("000001.SZ", status_tags=["st"])
        assert isinstance(ratio, float)

    def test_compute_limit_prices_method(self, rules):
        """测试 compute_limit_prices 方法"""
        result = rules.compute_limit_prices(10.0)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(x, float) for x in result)

    def test_compute_limit_prices_for_stock_method(self, rules):
        """测试 compute_limit_prices_for_stock 方法"""
        result = rules.compute_limit_prices_for_stock(10.0, "688001.SH")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_is_within_price_limit_method(self, rules):
        """测试 is_within_price_limit 方法"""
        result = rules.is_within_price_limit(10.5, 10.0)
        assert isinstance(result, bool)

    def test_is_within_price_limit_for_stock_method(self, rules):
        """测试 is_within_price_limit_for_stock 方法"""
        result = rules.is_within_price_limit_for_stock(10.5, 10.0, "000001.SZ")
        assert isinstance(result, bool)

    # ==================== 整手规则测试 ====================

    def test_get_min_lot_method(self, rules):
        """测试 get_min_lot 方法"""
        min_lot = rules.get_min_lot()
        assert isinstance(min_lot, int)
        assert min_lot > 0

    def test_get_lot_step_method(self, rules):
        """测试 get_lot_step 方法"""
        lot_step = rules.get_lot_step()
        assert isinstance(lot_step, int)
        assert lot_step > 0

    def test_is_valid_quantity_method(self, rules):
        """测试 is_valid_quantity 方法"""
        result = rules.is_valid_quantity(100)
        assert isinstance(result, bool)

    def test_is_valid_quantity_for_stock_method(self, rules):
        """测试 is_valid_quantity_for_stock 方法"""
        result = rules.is_valid_quantity_for_stock(100, "000001.SZ")
        assert isinstance(result, bool)

    def test_floor_quantity_method(self, rules):
        """测试 floor_quantity 方法"""
        result = rules.floor_quantity(150)
        assert isinstance(result, int)
        assert result >= 0

    def test_floor_quantity_for_stock_method(self, rules):
        """测试 floor_quantity_for_stock 方法"""
        result = rules.floor_quantity_for_stock(150, "000001.SZ")
        assert isinstance(result, int)
        assert result >= 0

    # ==================== 交收规则测试 ====================

    def test_get_settlement_period_method(self, rules):
        """测试 get_settlement_period 方法"""
        period = rules.get_settlement_period()
        assert isinstance(period, int)
        assert period >= 0

    def test_is_allowed_to_sell_method(self, rules):
        """测试 is_allowed_to_sell 方法"""
        result = rules.is_allowed_to_sell(0)
        assert isinstance(result, bool)

    # ==================== 元数据测试 ====================

    def test_get_name_method(self, rules):
        """测试 get_name 方法"""
        name = rules.get_name()
        assert isinstance(name, str)

    def test_get_description_method(self, rules):
        """测试 get_description 方法"""
        description = rules.get_description()
        assert isinstance(description, str)

    def test_get_profile_id_method(self, rules):
        """测试 get_profile_id 方法"""
        profile_id = rules.get_profile_id()
        assert isinstance(profile_id, str)
        assert profile_id == "china_a_stock"


class TestMarketsAPI:
    """测试所有市场的API一致性"""

    @pytest.mark.parametrize("market_id", [
        "china_a_stock",
        "hong_kong",
        "us_stock",
        "commodity_future",
        "forex",
        "crypto",
    ])
    def test_market_exists(self, market_id):
        """测试所有市场都存在"""
        proxy = MarketRulesProxy()
        assert proxy.is_available(market_id)

    @pytest.mark.parametrize("market_id", [
        "china_a_stock",
        "hong_kong",
        "us_stock",
        "commodity_future",
        "forex",
        "crypto",
    ])
    def test_market_has_required_methods(self, market_id):
        """测试所有市场都有必需的方法"""
        proxy = MarketRulesProxy()
        rules = proxy.get_market(market_id)

        # 必需方法列表
        required_methods = [
            'get_limit_ratio',
            'get_limit_ratio_for_stock',
            'compute_limit_prices',
            'compute_limit_prices_for_stock',
            'is_within_price_limit',
            'is_within_price_limit_for_stock',
            'is_at_limit_up',
            'is_at_limit_down',
            'get_min_lot',
            'get_lot_step',
            'is_valid_quantity',
            'is_valid_quantity_for_stock',
            'floor_quantity',
            'floor_quantity_for_stock',
            'get_settlement_period',
            'is_allowed_to_sell',
            'get_name',
            'get_description',
            'get_profile_id',
        ]

        for method in required_methods:
            assert hasattr(rules, method), f"{market_id} missing method: {method}"
            assert callable(getattr(rules, method)), f"{market_id}.{method} is not callable"

    @pytest.mark.parametrize("market_id", [
        "china_a_stock",
        "hong_kong",
        "us_stock",
        "commodity_future",
        "forex",
        "crypto",
    ])
    def test_market_has_required_properties(self, market_id):
        """测试所有市场都有必需的属性"""
        proxy = MarketRulesProxy()
        rules = proxy.get_market(market_id)

        # 必需属性列表
        required_properties = [
            'profile_id',
            'name',
            'description',
        ]

        for prop in required_properties:
            assert hasattr(rules, prop), f"{market_id} missing property: {prop}"


class TestAPIStability:
    """API稳定性测试（确保接口不破坏）"""

    def test_proxy_methods_signature(self):
        """测试 Proxy 方法签名稳定"""
        proxy = MarketRulesProxy()

        # 这些调用不应该抛出异常
        proxy.mount("us_stock")
        proxy.current
        proxy.get_market("china_a_stock")
        proxy.list_available()
        proxy.is_available("hong_kong")
        proxy.get_mounted_id()

    def test_rules_methods_signature(self):
        """测试 Rules 方法签名稳定"""
        proxy = MarketRulesProxy()
        rules = proxy.current

        # 这些调用不应该抛出异常
        rules.get_limit_ratio()
        rules.get_limit_ratio_for_stock("000001.SZ")
        rules.compute_limit_prices(10.0)
        rules.compute_limit_prices_for_stock(10.0, "000001.SZ")
        rules.is_within_price_limit(10.5, 10.0)
        rules.is_within_price_limit_for_stock(10.5, 10.0, "000001.SZ")
        rules.get_min_lot()
        rules.get_lot_step()
        rules.is_valid_quantity(100)
        rules.is_valid_quantity_for_stock(100, "000001.SZ")
        rules.floor_quantity(150)
        rules.floor_quantity_for_stock(150, "000001.SZ")
        rules.get_settlement_period()
        rules.is_allowed_to_sell(0)
        rules.get_name()
        rules.get_description()
        rules.get_profile_id()

    def test_return_types_stable(self):
        """测试返回类型稳定"""
        proxy = MarketRulesProxy()
        rules = proxy.current

        # 类型检查
        assert isinstance(rules.profile_id, str)
        assert isinstance(rules.name, str)
        assert isinstance(rules.description, str)
        assert isinstance(rules.get_limit_ratio(), float)
        assert isinstance(rules.compute_limit_prices(10.0), tuple)
        assert isinstance(rules.get_min_lot(), int)
        assert isinstance(rules.is_allowed_to_sell(0), bool)