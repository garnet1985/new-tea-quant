"""StrategyContext 与钩子载荷。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.hook_params import (
    CalendarSlice,
    Records,
    open_context,
)

pytestmark = pytest.mark.force_run


def _settings() -> StrategySettings:
    settings = StrategySettings.from_dict({})
    settings.apply_defaults()
    return settings


def test_open_context_keeps_sample_list_and_mode() -> None:
    ctx = open_context(
        strategy_key="demo/rsi",
        settings=_settings(),
        sample_list=["000001.SZ"],
        strategy_path="/tmp/demo",
    )
    assert ctx.info.key == "demo/rsi"
    assert ctx.info.path == "/tmp/demo"
    assert ctx.sample_list == ("000001.SZ",)
    assert ctx.mode == "entity_based"
    assert ctx.base_data_key


def test_state_is_a_shared_bag() -> None:
    bag = {}
    ctx = open_context(
        strategy_key="demo",
        settings=_settings(),
        sample_list=["000001.SZ"],
        state=bag,
    )
    ctx.state["last_rsi"] = 28.5
    assert bag["last_rsi"] == 28.5
    assert ctx.state.get("missing") is None


def test_effective_settings_dict_is_cached() -> None:
    ctx = open_context(
        strategy_key="demo",
        settings=_settings(),
        sample_list=["000001.SZ"],
    )
    assert ctx.effective_settings_dict() is ctx.effective_settings_dict()


def test_records_shortcuts() -> None:
    rows = [
        {"date": "20240109", "close": 10},
        {"date": "20240110", "close": 11},
        {"date": "20240111", "close": 12},
    ]
    records = Records(
        entity_id="000001.SZ",
        items={"k": rows},
        base_data_key="k",
    )
    assert records.record_of_today == {"date": "20240111", "close": 12}
    assert records.get_record("20240110")["close"] == 11
    assert [row["close"] for row in records.get_records("20240110", "20240111")] == [11, 12]
    assert records.last(2) == rows[-2:]
    assert Records(base_data_key="k").record_of_today is None


def test_calendar_slice_loads_on_read() -> None:
    loaded = {"calls": 0}

    def loader():
        loaded["calls"] += 1
        return {"000001.SZ": {"k": [{"date": "20240110", "close": 11}]}}

    calendar_slice = CalendarSlice(flags={"is_first_open_of_month": True}, base_data_key="k", loader=loader)
    assert calendar_slice.is_first_open_of_month is True
    assert loaded["calls"] == 0
    assert calendar_slice.ids() == ["000001.SZ"]
    assert calendar_slice.records_of("000001.SZ").record_of_today["close"] == 11
    assert loaded["calls"] == 1
    assert "as_of_date" not in calendar_slice.flags
