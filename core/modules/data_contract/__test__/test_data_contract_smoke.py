"""DataContract 冒烟：issue 形态与 mapping 一致（不连 DB）。"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    _pd = types.ModuleType("pandas")
    _pd.DataFrame = object  # type: ignore[attr-defined]
    sys.modules["pandas"] = _pd

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import ContractScope
from core.modules.data_contract.contracts import DataKey, IssueResult
from core.modules.data_contract.contracts import NonTimeSeriesContract, TimeSeriesContract
from core.modules.data_contract.core.cache.default_store import reset_shared_contract_cache
from core.modules.data_contract.core.load.loaders import StockKlineLoader, StockListLoader, TagLoader


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_shared_contract_cache()
    yield
    reset_shared_contract_cache()


@pytest.fixture
def dcm() -> DataContracts:
    return DataContracts(cache_enabled=False)


def test_stock_list_issue_shape(dcm: DataContracts):
    mgr = dcm._manager

    def _fake_load(contract, spec, eff_start, eff_end):
        contract.data = [{"id": "600000.SH"}]

    with patch.object(mgr, "_load_global_contract", side_effect=_fake_load):
        result = dcm.issue(DataKey.STOCK_LIST)

    assert isinstance(result, IssueResult)
    c = result.require_contract()
    assert c.meta.data_id == DataKey.STOCK_LIST
    assert c.meta.scope == ContractScope.GLOBAL
    assert isinstance(c, NonTimeSeriesContract)
    assert isinstance(c.loader, StockListLoader)
    assert c.data == [{"id": "600000.SH"}]


def test_kline_qfq_issue_shape(dcm: DataContracts):
    result = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        adjust="qfq",
        should_load_initially=False,
    )
    assert isinstance(result, IssueResult)
    assert result.entity_count == 1
    c = result.require_one()
    assert c.meta.data_id == DataKey.STOCK_KLINE_DAILY
    assert c.meta.scope == ContractScope.PER_ENTITY
    assert isinstance(c, TimeSeriesContract)
    assert isinstance(c.loader, StockKlineLoader)
    assert c.loader_params.get("adjust") == "qfq"
    assert c.loader_params.get("term") == "daily"
    assert c.data is None


def test_tag_issue_shape(dcm: DataContracts):
    result = dcm.issue(
        DataKey.TAG,
        entity_id="000001.SZ",
        should_load_initially=False,
    )
    c = result.require_one()
    assert c.meta.data_id == DataKey.TAG
    assert isinstance(c, TimeSeriesContract)
    assert isinstance(c.loader, TagLoader)
    assert getattr(c, "time_axis_field", None) == "as_of_date"
    assert c.data is None


def test_tag_load_requires_scenario(dcm: DataContracts):
    with pytest.raises(ValueError, match="scenario"):
        dcm.issue(
            DataKey.TAG,
            entity_id="000001.SZ",
            should_load_initially=False,
        ).require_one().load(start="20200101", end="20201231")


def test_until_prefix(dcm: DataContracts):
    result = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        adjust="qfq",
        should_load_initially=False,
    )
    contract = result.require_one()
    contract.data = [
        {"date": "20240101", "close": 1.0},
        {"date": "20240105", "close": 2.0},
        {"date": "20240110", "close": 3.0},
    ]
    assert len(dcm.until(contract, "20240104").rows) == 1
    assert len(dcm.until(contract, "20240110").rows) == 3
    dcm.until(contract, "20240105", reset=True)
    assert len(dcm.until(contract, "20240105").rows) == 2
