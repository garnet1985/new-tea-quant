"""_stock_ids_for_enumerator_view 使用 all_stocks 参数，非未定义 universe。"""
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.launcher.enumerator_runtime_service import (
    _stock_ids_for_enumerator_view,
)


def test_stock_ids_without_sampling():
    stocks = [{"id": "000001.SZ"}, {"id": "600000.SH"}]
    view = StrategySettingsView.from_dict(
        {"name": "t", "description": "d", "sampling": {"use_sampling": False}}
    )
    ids = _stock_ids_for_enumerator_view(
        strategy_name="example",
        settings_view=view,
        all_stocks=stocks,
    )
    assert ids == ["000001.SZ", "600000.SH"]
