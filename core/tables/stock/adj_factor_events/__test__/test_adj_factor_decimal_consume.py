"""消费路径：infra 读出口已规范为 float，业务层不再处理 Decimal。"""
import pytest

from core.modules.data_manager.data_services.stock.sub_services.kline_service import (
    KlineService,
)
from core.tables.stock.adj_factor_events.model import DataAdjFactorEventModel


class TestFloatConsumePath:
    def test_segment_offset_with_float_anchors(self):
        event = {
            "factor": 181.704,
            "qfq_anchor": 7.19,
            "raw_anchor": 7.19,
            "qfq_diff": 0.0,
        }
        off = KlineService._segment_offset_from_event(
            event,
            factor_eff=181.704,
            factor_latest=181.704,
        )
        assert off == pytest.approx(0.0, abs=1e-6)

    def test_qfq_price_latest_segment_matches_anchor(self):
        event = {
            "factor": 181.704,
            "qfq_anchor": 7.19,
            "raw_anchor": 7.19,
        }
        off = KlineService._segment_offset_from_event(
            event,
            factor_eff=181.704,
            factor_latest=181.704,
        )
        qfq = KlineService._qfq_price_from_raw(
            7.19,
            factor_eff=181.704,
            factor_latest=181.704,
            segment_offset=off,
        )
        assert qfq == pytest.approx(7.19, abs=1e-3)

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
