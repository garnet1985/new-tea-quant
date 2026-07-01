"""DataContracts Facade API 契约测试（api.yaml 0.5.0）。"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    sys.modules["pandas"] = types.ModuleType("pandas")

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import ContractScope, ContractType, DataKey
from core.modules.data_contract.core.cache.default_store import reset_shared_contract_cache


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_shared_contract_cache()
    yield
    reset_shared_contract_cache()


@pytest.fixture
def dcm() -> DataContracts:
    return DataContracts(cache_enabled=False)


def test_init_default_cache_enabled():
    facade = DataContracts()
    assert facade._cache_enabled is True


def test_info_stock_list(dcm: DataContracts):
    info = dcm.info(DataKey.STOCK_LIST)
    assert info.data_key == DataKey.STOCK_LIST
    assert info.scope == ContractScope.GLOBAL
    assert info.contract_type == ContractType.NON_TIME_SERIES
    assert info.has_cache is False  # cache_enabled=False in fixture
    assert info.supports_start_end is False


def test_info_kline_per_entity_no_cache(dcm: DataContracts):
    info = dcm.info(DataKey.STOCK_KLINE_DAILY)
    assert info.scope == ContractScope.PER_ENTITY
    assert info.has_cache is False
    assert info.time_axis_field == "date"


def test_issue_should_load_initially_false(dcm: DataContracts):
    result = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        adjust="qfq",
        should_load_initially=False,
    )
    assert result.by_entity is not None
    assert result.by_entity["600000.SH"].data is None


def test_issue_per_entity_cache_override_raises(dcm: DataContracts):
    with pytest.raises(ValueError, match="不支持 cache"):
        dcm.issue(
            DataKey.STOCK_KLINE_DAILY,
            entity_id="600000.SH",
            use_cache=True,
        )


def test_load_after_issue(dcm: DataContracts):
    issued = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        adjust="qfq",
        should_load_initially=False,
    )
    contract = issued.require_one()

    with patch.object(contract.loader, "load_batch", return_value={"600000.SH": [{"date": "20240101"}]}):
        dcm.load(issued)

    assert contract.data == [{"date": "20240101"}]


def test_until_prefix(dcm: DataContracts):
    issued = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        adjust="qfq",
        should_load_initially=False,
    )
    contract = issued.require_one()
    contract.data = [
        {"date": "20240101", "close": 1.0},
        {"date": "20240105", "close": 2.0},
        {"date": "20240110", "close": 3.0},
    ]
    r1 = dcm.until(contract, "20240104")
    assert len(r1.rows) == 1
    r2 = dcm.until(contract, "20240110")
    assert len(r2.rows) == 3


def test_time_window_helpers(dcm: DataContracts):
    issued = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        start="20240101",
        end="20241231",
        adjust="qfq",
        should_load_initially=False,
    )
    contract = issued.require_one()
    assert dcm.get_start_time(contract) == "20240101"
    assert dcm.get_end_time(contract) == "20241231"
    window = dcm.get_data_window(contract)
    assert window is not None
    assert window.start == "20240101"


def test_is_loaded_and_row_count(dcm: DataContracts):
    issued = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        should_load_initially=False,
    )
    contract = issued.require_one()
    assert dcm.is_loaded(contract) is False
    contract.data = [{"date": "20240101"}, {"date": "20240102"}]
    assert dcm.is_loaded(contract) is True
    assert dcm.row_count(contract) == 2


def test_until_cursor_multi_source(dcm: DataContracts):
    gdp = dcm.issue(DataKey.MACRO_LPR, should_load_initially=False).require_contract()
    gdp.data = [{"date": "20200101", "value": 1.0}, {"date": "20200105", "value": 2.0}]
    kline = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        should_load_initially=False,
    ).require_one()
    kline.data = [
        {"date": "20200101", "close": 1.0},
        {"date": "20200110", "close": 2.0},
    ]
    dcm.open_until_cursor("worker", contracts={DataKey.MACRO_LPR: gdp, DataKey.STOCK_KLINE_DAILY: kline})
    view = dcm.until_cursor("worker", "20200110")
    assert len(view[DataKey.MACRO_LPR]) == 2
    assert len(view[DataKey.STOCK_KLINE_DAILY]) == 2
    dcm.close_until_cursor("worker")


def test_issue_with_preloaded_data_zero_io(dcm: DataContracts):
    rows = [{"date": "20240101", "close": 1.0}, {"date": "20240102", "close": 2.0}]
    contract = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        adjust="qfq",
        data=rows,
    ).require_one()
    assert contract.data == rows
    assert contract.loader is not None


def test_issue_global_with_preloaded_data(dcm: DataContracts):
    rows = [{"symbol": "600000.SH", "name": "浦发银行"}]
    contract = dcm.issue(DataKey.STOCK_LIST, data=rows).require_contract()
    assert contract.data == rows


def test_merge_append_tail(dcm: DataContracts):
    issued = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        should_load_initially=False,
    )
    contract = issued.require_one()
    contract.data = [
        {"date": "20240101", "close": 1.0},
        {"date": "20240105", "close": 2.0},
    ]
    result = contract.merge([
        {"date": "20240103", "close": 9.0},  # overlap — discarded
        {"date": "20240110", "close": 3.0},
    ])
    assert result.added_rows == 1
    assert result.total_rows == 3
    assert [r["date"] for r in contract.data] == ["20240101", "20240105", "20240110"]


def test_drop_and_reset_until_cursor(dcm: DataContracts):
    issued = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        should_load_initially=False,
    )
    contract = issued.require_one()
    contract.data = [
        {"date": "20240101", "close": 1.0},
        {"date": "20240105", "close": 2.0},
        {"date": "20240110", "close": 3.0},
    ]
    dcm.until(contract, "20240110")
    drop = contract.drop("20240105")
    assert drop.dropped_rows == 1
    assert drop.total_rows == 2

    dcm.reset_until_cursor(contract)
    r = dcm.until(contract, "20240110")
    assert len(r.rows) == 2
    assert r.rows[0]["date"] == "20240105"


def test_merge_visible_to_live_cursor(dcm: DataContracts):
    issued = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        should_load_initially=False,
    )
    contract = issued.require_one()
    contract.data = [{"date": "20240101", "close": 1.0}]
    dcm.until(contract, "20240101")
    contract.merge([{"date": "20240105", "close": 2.0}])
    r = dcm.until(contract, "20240105")
    assert len(r.rows) == 2
