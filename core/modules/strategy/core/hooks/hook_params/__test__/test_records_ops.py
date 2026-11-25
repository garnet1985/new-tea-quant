"""Records 跨键 / 实体 / 持仓助手。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.hooks.hook_params import Records

pytestmark = pytest.mark.force_run


def test_has_keys_field_info() -> None:
    records = Records(
        entity_id="000001.SZ",
        entity_info={"id": "000001.SZ", "industry": "银行"},
        items={
            "k": [{"date": "20240110", "close": 10.0}],
            "stock.kline.weekly": [{"date": "20240108", "close": 9.5}],
            "empty": [],
        },
        base_data_key="k",
    )
    assert records.has("k") is True
    assert records.has("empty") is False
    assert records.has("missing") is False
    assert records.keys() == ["k", "stock.kline.weekly"]
    assert records.field("close") == 10.0
    assert records.field("close", "stock.kline.weekly") == 9.5
    assert records.info("industry") == "银行"
    assert records.info("missing", "x") == "x"


def test_position_helpers() -> None:
    rows = [
        {"date": "20240108", "close": 9.0},
        {"date": "20240109", "close": 10.0},
        {"date": "20240110", "close": 12.0},
    ]
    records = Records(
        items={"k": rows},
        base_data_key="k",
        position={
            "entry_date": "20240109",
            "entry_price": 10.0,
            "remaining_ratio": 1.0,
        },
    )
    assert records.in_position is True
    assert records.unrealized_pnl_pct() == pytest.approx(0.2)
    assert records.holding_bars() == 2

    flat = Records(
        items={"k": rows},
        base_data_key="k",
        position={"entry_price": 10.0, "remaining_ratio": 0.0},
    )
    assert flat.in_position is False
    assert flat.unrealized_pnl_pct() is None
    assert flat.holding_bars() is None


def test_holding_bars_aligns_forward_when_entry_missing() -> None:
    rows = [
        {"date": "20240108", "close": 9.0},
        {"date": "20240110", "close": 11.0},
        {"date": "20240111", "close": 12.0},
    ]
    records = Records(
        items={"k": rows},
        base_data_key="k",
        position={
            "entry_date": "20240109",  # 不在序列里 → 落到 20240110
            "entry_price": 10.0,
            "remaining_ratio": 0.5,
        },
    )
    assert records.holding_bars() == 2


def test_align_both_rising_crossed_on() -> None:
    records = Records(
        items={
            "k": [
                {"date": "20240108", "close": 10.0, "sma": 11.0},
                {"date": "20240109", "close": 10.5, "sma": 11.0},  # 仍在下
                {"date": "20240110", "close": 12.0, "sma": 11.0},  # 刚上穿
            ],
            "stock.kline.weekly": [
                {"date": "20240103", "close": 9.0},
                {"date": "20240108", "close": 10.5},
                # 无 20240110 → align 落到 20240108
            ],
        },
        base_data_key="k",
    )
    aligned = records.align("stock.kline.weekly")
    assert aligned is not None
    assert aligned["date"] == "20240108"
    assert aligned["close"] == 10.5
    assert records.align("stock.kline.weekly", as_of="20240103")["close"] == 9.0

    assert records.both_rising("close", "", "stock.kline.weekly") is True
    assert records.both_rising("close", key_b="") is False

    assert records.crossed_on("k", "close", "sma") is True
    assert records.crossed_on("k", "close", "sma", below=True) is False
