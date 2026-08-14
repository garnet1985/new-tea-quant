"""ListService period 查询 survivorship 模式。"""
from unittest.mock import MagicMock

from core.modules.data_manager.core.data_services.stock.sub_services.list_service import (
    SURVIVORSHIP_PIT,
    SURVIVORSHIP_SURVIVOR,
    ListService,
    _PERIOD_WHERE,
)


def _make_svc():
    dm = MagicMock()
    stock_list_model = MagicMock()
    stock_list_model.load.return_value = []
    dm.get_table.return_value = stock_list_model
    return ListService(dm), stock_list_model


def test_period_load_pit_uses_period_start_as_delist_bound():
    svc, model = _make_svc()
    svc.load(period_start="20200101", period_end="20241231", survivorship=SURVIVORSHIP_PIT)
    model.load.assert_called_once_with(
        _PERIOD_WHERE,
        ("20241231", "20200101"),
        order_by="id ASC",
    )


def test_period_load_survivor_uses_period_end_as_delist_bound():
    svc, model = _make_svc()
    svc.load(period_start="20200101", period_end="20241231", survivorship=SURVIVORSHIP_SURVIVOR)
    model.load.assert_called_once_with(
        _PERIOD_WHERE,
        ("20241231", "20241231"),
        order_by="id ASC",
    )


def test_normalize_survivorship_defaults_unknown_to_pit():
    assert ListService.normalize_survivorship(None) == SURVIVORSHIP_PIT
    assert ListService.normalize_survivorship("unknown") == SURVIVORSHIP_PIT
    assert ListService.normalize_survivorship("SURVIVOR") == SURVIVORSHIP_SURVIVOR
