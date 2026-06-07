import pytest
from unittest.mock import MagicMock

from core.tables.stock.adj_factor_events.model import DataAdjFactorEventModel


def _model_with_stubs():
    db = MagicMock()
    db.config = {"database_type": "duckdb"}
    return DataAdjFactorEventModel(db=db)


class TestAdjFactorEventModel:
    def test_load_effective_events_for_dates_strict(self):
        model = _model_with_stubs()
        events = [
            {"id": "000001.SZ", "event_date": "20250105", "qfq_diff": 1.25},
        ]
        model.load = lambda condition, params, order_by=None: events  # type: ignore[assignment]
        model.load_one = lambda condition, params, order_by=None: None  # type: ignore[assignment]

        out = model.load_effective_events_for_dates(
            "000001.SZ",
            ["20250101", "20250110"],
            is_strict=True,
        )

        assert out["20250101"]["is_adjusted"] is False
        assert out["20250101"]["qfq_diff"] == 0.0
        assert out["20250110"]["is_adjusted"] is True
        assert out["20250110"]["is_inferred"] is False
        assert out["20250110"]["qfq_diff"] == pytest.approx(1.25)

    def test_load_effective_events_for_dates_default_infers_earliest(self):
        model = _model_with_stubs()
        model.load = lambda condition, params, order_by=None: []  # type: ignore[assignment]
        model.load_one = lambda condition, params, order_by=None: {  # type: ignore[assignment]
            "id": "000001.SZ",
            "event_date": "20250120",
            "qfq_diff": 2.5,
        }

        out = model.load_effective_events_for_dates(
            "000001.SZ",
            ["20250101", "20250110"],
            is_strict=False,
        )

        assert out["20250101"]["is_adjusted"] is True
        assert out["20250101"]["is_inferred"] is True
        assert out["20250101"]["qfq_diff"] == pytest.approx(2.5)
        assert out["20250110"]["is_adjusted"] is True
        assert out["20250110"]["is_inferred"] is True

    def test_load_effective_events_for_dates_no_events(self):
        model = _model_with_stubs()
        model.load = lambda condition, params, order_by=None: []  # type: ignore[assignment]
        model.load_one = lambda condition, params, order_by=None: None  # type: ignore[assignment]

        out = model.load_effective_events_for_dates(
            "000001.SZ",
            ["20250101", "20250110"],
            is_strict=False,
        )

        assert out["20250101"]["is_adjusted"] is False
        assert out["20250110"]["is_adjusted"] is False
        assert out["20250101"]["qfq_diff"] == 0.0
        assert out["20250110"]["qfq_diff"] == 0.0

    def test_load_effective_events_from_join_rows_default(self):
        model = _model_with_stubs()
        model.load = lambda condition, params, order_by=None: []  # type: ignore[assignment]
        model.load_one = lambda condition, params, order_by=None: None  # type: ignore[assignment]
        rows = [
            {"id": "000001.SZ", "date": "20250101", "adj_event_date": None, "adj_qfq_diff": None, "adj_factor": None},
            {"id": "000001.SZ", "date": "20250110", "adj_event_date": "20250105", "adj_qfq_diff": 1.2, "adj_factor": 0.9},
        ]

        out = model.load_effective_events_from_join_rows(
            stock_id="000001.SZ",
            rows=rows,
            is_strict=False,
        )

        assert out["20250101"]["is_inferred"] is True
        assert out["20250101"]["is_adjusted"] is True
        assert out["20250110"]["is_inferred"] is False
        assert out["20250110"]["qfq_diff"] == pytest.approx(1.2)

