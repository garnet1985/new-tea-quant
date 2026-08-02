#!/usr/bin/env python3
"""Strategy API contract tests (骨架).

遵循 CORE_MODULE_STANDARDS.md 规范：
- test_cases.yaml 定义测试注册表
- 覆盖 api.yaml 中定义的稳定 API
- 当前只定义测试类和方法名，不实现测试逻辑
"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestApi(unittest.TestCase):
    """Strategy API 契约测试"""

    def test_facade_export(self):
        """facade 导出 Strategy 类"""
        # TODO: 实现测试逻辑
        pass

    def test_scan_api(self):
        """scan API 可调用且参数正确（实现见 test_scanner_api.py）。"""
        from core.modules.strategy import Strategy

        self.assertTrue(callable(Strategy.scan))

    def test_enumerate_api(self):
        """enumerate API 可调用且参数正确"""
        # TODO: 实现测试逻辑
        pass

    def test_analyze_api(self):
        """analyze API 可调用且参数正确"""
        from core.modules.strategy import Strategy

        self.assertTrue(callable(Strategy.analyze))

    def test_list_strategies_api(self):
        """list_strategies API 可调用"""
        # TODO: 实现测试逻辑
        pass

    def test_get_strategy_info_api(self):
        """get_strategy_info API 可调用且参数正确"""
        # TODO: 实现测试逻辑
        pass


class TestContracts(unittest.TestCase):
    """Strategy contracts 类型与枚举"""

    def test_execution_mode_enum(self):
        """ExecutionMode 枚举定义正确"""
        # TODO: 实现测试逻辑
        pass

    def test_sell_reason_enum(self):
        """SellReason 枚举定义正确"""
        # TODO: 实现测试逻辑
        pass

    def test_simulate_kind_enum(self) -> None:
        """SimulateKind 枚举定义正确"""
        from core.modules.strategy.contracts import SimulateKind

        self.assertEqual(SimulateKind.ENUMERATE.value, "enumerate")

    def test_hook_types_exported_from_contracts(self) -> None:
        """hooks 契约与数据类型均从 contracts 公开"""
        from core.modules.strategy import Strategy
        from core.modules.strategy.contracts import StrategyContext, StrategyHooks
        from core.modules.strategy.contracts import CalendarAsOfResult, Opportunity

        self.assertTrue(issubclass(StrategyHooks, object))
        self.assertEqual(StrategyContext.__name__, "StrategyContext")
        opp = Opportunity(stock={}, record_of_today={"close": 1.0})
        self.assertEqual(opp.trigger_price, 1.0)
        result = CalendarAsOfResult(as_of_date="20240102", stocks=[])
        self.assertEqual(result.session_state, {})


class TestIntegration(unittest.TestCase):
    """Strategy facade 集成验证"""

    def test_strategy_scan_api(self):
        """Strategy.scan() 可调用"""
        # TODO: 实现测试逻辑
        pass

    def test_strategy_enumerate_api(self):
        """Strategy.enumerate() 可调用"""
        # TODO: 实现测试逻辑
        pass

    def test_strategy_list_strategies_api(self):
        """Strategy discovery 列表可用"""
        # TODO: 实现测试逻辑
        pass


if __name__ == "__main__":
    unittest.main()