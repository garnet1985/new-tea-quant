"""ListService.load_filter_options。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.modules.data_manager.core.data_services.stock.sub_services.list_service import (
    ListService,
)

pytestmark = pytest.mark.force_run


def _svc() -> tuple[ListService, MagicMock, MagicMock, MagicMock, MagicMock]:
    dm = MagicMock()
    boards = MagicMock()
    markets = MagicMock()
    areas = MagicMock()
    sw = MagicMock()

    def _table(name: str):
        return {
            "sys_data_stock_list": MagicMock(),
            "sys_data_boards": boards,
            "sys_data_markets": markets,
            "sys_data_areas": areas,
            "sys_data_sw_industry": sw,
            "sys_map_sw_stock_industry": MagicMock(),
            "sys_map_stock_board": MagicMock(),
            "sys_map_stock_market": MagicMock(),
            "sys_map_stock_area": MagicMock(),
        }[name]

    dm.get_table.side_effect = _table
    return ListService(dm), boards, markets, areas, sw


def test_load_filter_options_list_status_fixed() -> None:
    svc, *_ = _svc()
    out = svc.load_filter_options("list_status")
    assert [r["value"] for r in out["list_status"]] == ["L", "D", "P"]


def test_load_filter_options_board_alive_only() -> None:
    svc, boards, *_ = _svc()
    boards.load.return_value = [
        {"value": "创业板", "is_alive": 1},
        {"value": "主板", "is_alive": 1},
    ]
    out = svc.load_filter_options("board", alive_only=True)
    assert [r["value"] for r in out["board"]] == ["主板", "创业板"]
    boards.load.assert_called_once_with("is_alive = %s", (1,))


def test_load_filter_options_industry_l1() -> None:
    svc, _b, _m, _a, sw = _svc()
    sw.load.return_value = [
        {"id": "801780.SI", "name": "银行", "level": "L1"},
        {"id": "801010.SI", "name": "农林牧渔", "level": "L1"},
    ]
    out = svc.load_filter_options("industry")
    assert out["industry"][0]["value"] == "农林牧渔"
    assert out["industry"][0]["code"] == "801010.SI"
    sw.load.assert_called_once_with("level = %s", ("L1",))


def test_load_filter_options_rejects_unknown_dim() -> None:
    svc, *_ = _svc()
    with pytest.raises(ValueError, match="未知 filter 维度"):
        svc.load_filter_options("sector")
