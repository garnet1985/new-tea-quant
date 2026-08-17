"""ScannerCalendarAsof 单元测试（无 DB）。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.scanner.helpers.calendar_asof import (
    ScannerCalendarAsof,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime

pytestmark = pytest.mark.force_run


def test_build_calendar_view_year_end() -> None:
    opens = ["20250102", "20251231", "20260105"]
    cal = ScannerCalendarAsof._build_calendar_view(
        "20251231",
        opens,
        rebalance_period="year",
        open_date_index=1,
    )
    assert cal["is_period_end"] is True
    assert cal["is_period_start"] is False
    assert cal["is_last_open_of_year"] is True


def test_filter_stock_ids_passthrough_without_asof_override() -> None:
    class _Hooks(StrategyHooks):
        def has_opportunity(self, ctx):  # noqa: ANN001
            return False

    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    runtime = StrategyHookRuntime(_Hooks(), strategy_name="demo", settings=settings)
    assert runtime.is_overridden("on_calendar_asof") is False

    info = SimpleNamespace(
        key="demo",
        unique_relative_path="demo",
        hooks_module_path="",
        hooks_class=_Hooks,
        strategy_file=SimpleNamespace(resolve=lambda: ""),
    )
    # from_strategy_info 需要 module_path；直接测未 override 早退：空 hooks 路径会失败并保持原列表
    out = ScannerCalendarAsof.filter_stock_ids(
        strategy_info=info,
        settings=settings,
        stock_ids=["600000.SH", "000001.SZ"],
        scan_date="20250102",
        data_manager=SimpleNamespace(service=None, stock=None),
    )
    assert out == ["600000.SH", "000001.SZ"]
