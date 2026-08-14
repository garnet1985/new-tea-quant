"""消费路径：infra 读出口已规范为 float，业务层不再处理 Decimal。"""
import pytest

from core.modules.data_manager.core.data_services.stock.sub_services.kline_service import (
    KlineService,
)
from core.tables.stock.adj_factor_events.model import DataAdjFactorEventModel


class TestFloatConsumePath:
    def test_global_offset_on_latest_event_day(self):
        events = [
            {
                "id": "000001.SZ",
                "event_date": "20250105",
                "factor": 2.0,
                "qfq_anchor": 5.0,
                "raw_anchor": 10.0,
            }
        ]
        ctx = KlineService._resolve_global_qfq_context(events, factor_latest=2.0)
        qfq = KlineService._qfq_price_global_offset(
            10.0,
            factor_eff=2.0,
            factor_latest=2.0,
            global_offset=ctx["global_offset"],
        )
        assert qfq == pytest.approx(5.0, abs=1e-6)

    def test_global_offset_ignores_segment_qfq_diff(self):
        kline = {
            "id": "000001.SZ",
            "open": 10.0,
            "close": 10.0,
            "high": 10.5,
            "low": 9.5,
            "pre_close": 9.8,
        }
        events = [
            {
                "id": "000001.SZ",
                "event_date": "20250105",
                "factor": 2.0,
                "qfq_anchor": 5.0,
                "raw_anchor": 10.0,
                "qfq_diff": 99.0,
            }
        ]
        ctx = KlineService._resolve_global_qfq_context(events, factor_latest=2.0)
        info = {"event": events[0], "qfq_diff": 99.0}
        KlineService._apply_qfq_from_event_info(
            KlineService,
            kline,
            info,
            factor_latest=2.0,
            global_qfq_context=ctx,
        )
        assert kline["close"] == pytest.approx(5.0)

    def test_apply_qfq_diff_fallback_only_without_anchors(self):
        kline = {
            "id": "000001.SZ",
            "close": 10.0,
            "open": 10.0,
            "high": 10.0,
            "low": 10.0,
            "pre_close": 10.0,
        }
        info = {
            "event": {
                "id": "000001.SZ",
                "event_date": "20250105",
                "factor": 2.0,
                "qfq_anchor": None,
                "raw_anchor": None,
                "qfq_diff": 1.5,
            },
            "qfq_diff": 1.5,
        }
        KlineService._apply_qfq_from_event_info(
            KlineService,
            kline,
            info,
            factor_latest=2.0,
            global_qfq_context={"use_global_offset": False, "global_offset": 0.0},
        )
        assert kline["close"] == pytest.approx(11.5)

    def test_join_rows_with_float_adj_columns(self):
        model = DataAdjFactorEventModel(db=None)
        rows = [
            {
                "id": "000001.SZ",
                "date": "20250110",
                "adj_event_date": "20250105",
                "adj_factor": 109.1694,
                "adj_qfq_anchor": 14.4,
                "adj_raw_anchor": 16.87,
                "adj_qfq_diff": 0.7152,
            }
        ]
        out = model.load_effective_events_from_join_rows(
            stock_id="000001.SZ",
            rows=rows,
            is_strict=False,
        )
        info = out["20250110"]
        assert info["is_adjusted"] is True
        ev = info["event"]
        assert ev["factor"] == pytest.approx(109.1694)
        assert ev["qfq_anchor"] == pytest.approx(14.4)

    def test_save_events_passes_through_without_handler_precision(self):
        """舍入在 adj_factor_event handler；Model 原样 upsert。"""
        captured = []
        model = DataAdjFactorEventModel(db=None)

        def _capture(rows, unique_keys=None):
            captured.extend(rows)
            return len(rows)

        model.upsert_many = _capture  # type: ignore[method-assign]
        model.save_events(
            [
                {
                    "id": "000001.SZ",
                    "event_date": "20230103",
                    "factor": 172.823612,
                    "qfq_anchor": 17.5678,
                    "raw_anchor": 18.2345,
                    "qfq_diff": 0.2209528,
                }
            ]
        )
        assert len(captured) == 1
        row = captured[0]
        assert row["factor"] == pytest.approx(172.823612)
        assert row["qfq_anchor"] == pytest.approx(17.5678)
        assert row["raw_anchor"] == pytest.approx(18.2345)
