"""Benchmark: until_cursor (hot API) vs single-contract until (sugar)."""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from typing import Any, Dict, List

import pytest

try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    sys.modules["pandas"] = types.ModuleType("pandas")

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey
from core.modules.data_contract.core.cache.default_store import reset_shared_contract_cache


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


def _gdp_rows() -> List[Dict[str, Any]]:
    return [{"quarter": f"2020Q{(i % 4) + 1}", "value": float(i)} for i in range(80)]


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_shared_contract_cache()
    yield
    reset_shared_contract_cache()


def _bench_until_cursor(dcm: DataContracts, as_ofs: List[str], *, rounds: int = 3) -> float:
    gdp = dcm.issue(DataKey.MACRO_GDP, should_load_initially=False).require_contract()
    gdp.data = _gdp_rows()
    kline = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        should_load_initially=False,
    ).require_one()
    kline.data = _kline_rows(_trading_dates(500))
    dcm.open_until_cursor("bench", contracts={DataKey.MACRO_GDP: gdp, DataKey.STOCK_KLINE_DAILY: kline})

    best = float("inf")
    for _ in range(rounds):
        dcm.reset_until_cursor_session("bench")
        t0 = time.perf_counter()
        for as_of in as_ofs:
            view = dcm.until_cursor("bench", as_of)
            assert view[DataKey.STOCK_KLINE_DAILY]
        best = min(best, time.perf_counter() - t0)
    dcm.close_until_cursor("bench")
    return best


def _bench_until_sugar_twice(dcm: DataContracts, as_ofs: List[str], *, rounds: int = 3) -> float:
    gdp = dcm.issue(DataKey.MACRO_GDP, should_load_initially=False).require_contract()
    gdp.data = _gdp_rows()
    kline = dcm.issue(
        DataKey.STOCK_KLINE_DAILY,
        entity_id="600000.SH",
        should_load_initially=False,
    ).require_one()
    kline.data = _kline_rows(_trading_dates(500))

    best = float("inf")
    for _ in range(rounds):
        dcm.reset_until_cursor(gdp)
        dcm.reset_until_cursor(kline)
        t0 = time.perf_counter()
        for as_of in as_ofs:
            assert dcm.until(gdp, as_of).rows
            assert dcm.until(kline, as_of).rows
        best = min(best, time.perf_counter() - t0)
    return best


def test_until_cursor_api_benchmark(capsys):
    dates = _trading_dates(500)
    as_ofs = dates[50:]
    dcm = DataContracts(cache_enabled=False)

    hot_s = _bench_until_cursor(dcm, as_ofs)
    sugar_s = _bench_until_sugar_twice(dcm, as_ofs)
    ratio = sugar_s / hot_s if hot_s > 0 else float("inf")

    msg = (
        f"\n--- until API benchmark (GDP + kline, {len(as_ofs)} as_of) ---\n"
        f"  until_cursor (1 call/source/step):  {hot_s * 1000:.2f} ms\n"
        f"  until() ×2 per as_of (sugar):       {sugar_s * 1000:.2f} ms\n"
        f"  ratio sugar/hot: {ratio:.3f}x\n"
    )
    print(msg)
    with capsys.disabled():
        print(msg)

    assert hot_s > 0
    assert sugar_s > 0
