"""指标落盘字段命名与 alias 校验。"""

from __future__ import annotations

import pytest

from core.modules.indicator import Indicator, field_naming
from core.modules.strategy.core.services.entity_loader.contract_indicators import (
    ContractIndicators,
)


def _klines(n: int = 60):
    return [
        {
            "open": float(i),
            "high": float(i + 1),
            "low": float(i - 1),
            "close": float(i),
            "volume": 1000,
        }
        for i in range(1, n + 1)
    ]


def test_series_default_and_alias():
    assert field_naming.series_field_name("ma", {"length": 20}) == "ma20"
    assert (
        field_naming.series_field_name("ma", {"length": 20, "alias": "slow_ma"})
        == "slow_ma"
    )


def test_dict_default_and_alias_prefix():
    assert (
        field_naming.dict_field_name("macd", {"fast": 12}, "MACDh_12_26_9")
        == "macdh_12_26_9"
    )
    assert (
        field_naming.dict_field_name(
            "macd", {"fast": 12, "alias": "macd"}, "MACDh_12_26_9"
        )
        == "macd_macdh_12_26_9"
    )


def test_validate_rejects_duplicate_alias():
    with pytest.raises(ValueError, match="重复"):
        field_naming.validate_indicators_config(
            {
                "ma": [
                    {"length": 5, "alias": "x"},
                    {"length": 10, "alias": "x"},
                ]
            }
        )


def test_validate_rejects_alias_collision_with_default():
    with pytest.raises(ValueError, match="重复"):
        field_naming.validate_indicators_config(
            {
                "ma": [{"length": 20}],
                "rsi": [{"length": 14, "alias": "ma20"}],
            }
        )


def test_validate_rejects_reserved_alias():
    with pytest.raises(ValueError, match="行情字段"):
        field_naming.validate_indicators_config(
            {"rsi": [{"length": 14, "alias": "close"}]}
        )


def test_compute_batch_strips_alias_but_keeps_in_returned_cfg():
    batch = list(
        Indicator.compute_batch(
            _klines(),
            {"ma": [{"length": 20, "alias": "slow_ma"}]},
        )
    )
    assert len(batch) == 1
    name, cfg, result = batch[0]
    assert name == "ma"
    assert cfg.get("alias") == "slow_ma"
    assert isinstance(result, list)
    assert result[-1] is not None


def test_contract_indicators_writes_alias_and_macd_channels():
    rows = [dict(k) for k in _klines(80)]
    ContractIndicators._apply_to_rows(
        rows,
        {
            "ma": [{"length": 20, "alias": "slow_ma"}],
            "macd": [{"fast": 12, "slow": 26, "signal": 9, "alias": "macd"}],
        },
    )
    last = rows[-1]
    assert last.get("slow_ma") is not None
    assert last.get("ma20") is None
    assert last.get("macd_macdh_12_26_9") is not None
    assert last.get("macd_macdh_12_26_9_fast12_signal9_slow26") is None
