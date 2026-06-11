"""adj_factor_events 精度与窄类型契约测试。"""
import pytest

from core.tables.stock.adj_factor_events.precision import (
    factor_tolerance,
    normalize_event_row,
    round_diff,
    round_factor,
    round_price,
)
from userspace.extensions.data_source.handlers.adj_factor_event.helper import (
    AdjFactorEventHandlerHelper as helper,
)


class TestNormalizeEventRow:
    def test_rounds_float_noise(self):
        row = normalize_event_row(
            {
                "factor": 172.82361234,
                "qfq_anchor": 17.56789,
                "raw_anchor": 18.23456,
                "qfq_diff": 0.2209528243,
            }
        )
        assert row["factor"] == pytest.approx(172.8236)
        assert row["qfq_anchor"] == pytest.approx(17.568)
        assert row["raw_anchor"] == pytest.approx(18.235)
        assert row["qfq_diff"] == pytest.approx(0.221)

    def test_rejects_decimal_at_write_boundary(self):
        from decimal import Decimal

        with pytest.raises(TypeError, match="Decimal"):
            normalize_event_row(
                {
                    "factor": Decimal("181.7040"),
                    "qfq_anchor": 7.19,
                    "raw_anchor": 7.19,
                    "qfq_diff": 0.0,
                }
            )

    def test_nullable_qfq_anchor(self):
        row = normalize_event_row(
            {"factor": 1.0, "qfq_anchor": None, "raw_anchor": 10.0, "qfq_diff": 0.0}
        )
        assert row["qfq_anchor"] is None


class TestChainTolerance:
    def test_chain_equal_within_factor_places(self):
        left = [("20240626", 181.7040)]
        right = [("20240626", 181.70395)]  # 噪声在 4 位精度内
        assert helper._chain_keys_equal(left, right)

    def test_chain_rejects_float_noise_beyond_rounded_places(self):
        left = [("20240626", 181.704)]
        right = [("20240626", 181.703)]
        assert not helper._chain_keys_equal(left, right)

    def test_chain_diff_beyond_factor_places(self):
        left = [("20240626", 181.704)]
        right = [("20240626", 181.703)]
        assert not helper._chain_keys_equal(left, right)

    def test_factor_tolerance_matches_places(self):
        assert factor_tolerance() == pytest.approx(0.0001)


class TestPackEventRow:
    def test_pack_applies_precision(self):
        row = helper._pack_event_row(
            stock_id="000002.SZ",
            event_date_ymd="20240626",
            factor=181.70381234,
            qfq_price=7.18999,
            raw_close=7.18999,
            qfq_diff=0.000012345,
        )
        assert row["factor"] == pytest.approx(181.7038)
        assert row["qfq_anchor"] == pytest.approx(7.19)
        assert row["qfq_diff"] == pytest.approx(0.0, abs=1e-3)
