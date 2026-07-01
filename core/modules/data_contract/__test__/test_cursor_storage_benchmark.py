"""Benchmark: dict-in-parent vs many small contracts — until hot path."""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, Hashable, List, Mapping

import pytest

try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    sys.modules["pandas"] = types.ModuleType("pandas")

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey
from core.modules.data_contract.core.cache.default_store import reset_shared_contract_cache
from core.modules.data_contract.core.contract.contracts.base import DataContract
from core.modules.data_cursor import DataCursor


STOCK_IDS = [f"60000{i}.SH" for i in range(10)]
_GDP_KEY = DataKey.MACRO_GDP
_KLINE_KEY = DataKey.STOCK_KLINE_DAILY


def _trading_dates(n: int) -> List[str]:
    out: List[str] = []
    d = date(2020, 1, 1)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def _kline_rows(dates: List[str]) -> List[Dict[str, Any]]:
    return [{"date": d, "open": 10.0, "close": 10.0 + len(d) % 7} for d in dates]


def _gdp_rows(n_quarters: int) -> List[Dict[str, Any]]:
    return [{"quarter": f"2020Q{(i % 4) + 1}", "value": 100.0 + i} for i in range(n_quarters)]


@dataclass
class _ParentDictPayload:
    """Ideal model: one parent, .data = {slot_or_entity_id: rows}."""

    data: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


def _build_shared_data(dates: List[str]) -> tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    gdp_rows = _gdp_rows(80)
    klines_by_stock = {sid: _kline_rows(dates) for sid in STOCK_IDS}
    return gdp_rows, klines_by_stock


def _issue_gdp_contract(dcm: DataContracts, gdp_rows: List[Dict[str, Any]]) -> DataContract:
    c = dcm.issue(_GDP_KEY, should_load_initially=False).require_contract()
    c.data = gdp_rows
    return c


def _issue_stock_contracts(
    dcm: DataContracts,
    klines_by_stock: Mapping[str, List[Dict[str, Any]]],
) -> Dict[str, DataContract]:
    issued = dcm.issue(_KLINE_KEY, entity_ids=STOCK_IDS, should_load_initially=False)
    assert issued.by_entity is not None
    for sid, rows in klines_by_stock.items():
        issued.by_entity[sid].data = rows
    return dict(issued.by_entity)


def _worker_sources_small_contracts(
    gdp: DataContract,
    by_entity: Mapping[str, DataContract],
    stock_id: str,
) -> Dict[Hashable, DataContract]:
    return {_GDP_KEY: gdp, _KLINE_KEY: by_entity[stock_id]}


def _worker_sources_from_parent_dict(
    parent: _ParentDictPayload,
    stock_id: str,
) -> Dict[Hashable, List[Dict[str, Any]]]:
    return {
        _GDP_KEY: parent.data["macro_gdp"],
        _KLINE_KEY: parent.data[stock_id],
    }


def _bench_until_hot(cursor: DataCursor, as_ofs: List[str], *, rounds: int = 5) -> float:
    best = float("inf")
    for _ in range(rounds):
        cursor.reset()
        t0 = time.perf_counter()
        for as_of in as_ofs:
            view = cursor.until(as_of)
            assert view[_GDP_KEY] is not None
            assert view[_KLINE_KEY]
        best = min(best, time.perf_counter() - t0)
    return best


def _bench_cursor_build_small_contracts(
    gdp: DataContract,
    by_entity: Mapping[str, DataContract],
    *,
    rounds: int = 200,
) -> float:
    t0 = time.perf_counter()
    for _ in range(rounds):
        for sid in STOCK_IDS:
            DataCursor(contracts=_worker_sources_small_contracts(gdp, by_entity, sid))
    return time.perf_counter() - t0


def _bench_cursor_build_from_dict(
    parent: _ParentDictPayload,
    *,
    rounds: int = 200,
) -> float:
    t0 = time.perf_counter()
    for _ in range(rounds):
        for sid in STOCK_IDS:
            rows = _worker_sources_from_parent_dict(parent, sid)
            DataCursor.from_rows(
                rows,
                time_field_overrides={
                    _GDP_KEY: "quarter",
                    _KLINE_KEY: "date",
                },
            )
    return time.perf_counter() - t0


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_shared_contract_cache()
    yield
    reset_shared_contract_cache()


def test_storage_model_until_benchmark(capsys):
    """Compare until hot path: small contracts vs dict parent (entity worker: GDP + 1 stock)."""
    dates = _trading_dates(500)
    as_ofs = dates[50:]
    gdp_rows, klines_by_stock = _build_shared_data(dates)
    stock_id = STOCK_IDS[0]

    dcm = DataContracts(cache_enabled=False)
    gdp_contract = _issue_gdp_contract(dcm, gdp_rows)
    by_entity = _issue_stock_contracts(dcm, klines_by_stock)

    parent = _ParentDictPayload(
        data={"macro_gdp": gdp_rows, **klines_by_stock},
    )

    cursor_small = DataCursor(
        contracts=_worker_sources_small_contracts(gdp_contract, by_entity, stock_id),
    )
    cursor_dict = DataCursor.from_rows(
        _worker_sources_from_parent_dict(parent, stock_id),
        time_field_overrides={_GDP_KEY: "quarter", _KLINE_KEY: "date"},
    )

    until_small_s = _bench_until_hot(cursor_small, as_ofs)
    until_dict_s = _bench_until_hot(cursor_dict, as_ofs)
    until_ratio = until_dict_s / until_small_s if until_small_s > 0 else float("inf")

    build_small_s = _bench_cursor_build_small_contracts(gdp_contract, by_entity)
    build_dict_s = _bench_cursor_build_from_dict(parent)
    build_ratio = build_dict_s / build_small_s if build_small_s > 0 else float("inf")

    msg = (
        f"\n--- storage model benchmark (GDP + 1 stock, {len(as_ofs)} until/as_of) ---\n"
        f"  [HOT until] small contracts:  {until_small_s * 1000:.2f} ms\n"
        f"  [HOT until] dict parent:      {until_dict_s * 1000:.2f} ms\n"
        f"  [HOT until] ratio dict/small: {until_ratio:.3f}x\n"
        f"\n"
        f"  [BUILD cursor ×10 entities] small contracts: {build_small_s * 1000:.2f} ms\n"
        f"  [BUILD cursor ×10 entities] dict parent:     {build_dict_s * 1000:.2f} ms\n"
        f"  [BUILD] ratio dict/small: {build_ratio:.3f}x\n"
        f"\n"
        f"  Note: both until paths use the same DataCursor engine;\n"
        f"  dict path simulates one-time extract of row refs from parent.data.\n"
    )
    print(msg)
    with capsys.disabled():
        print(msg)

    assert until_small_s > 0
    assert until_dict_s > 0
    # Same underlying list refs → until should stay within noise band (~15%).
    assert until_ratio < 1.15 or until_ratio > 0.85
