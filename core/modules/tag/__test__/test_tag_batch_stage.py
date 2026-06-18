from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.tag.engines.shared.staging.batch_stage import stage_entities_batch


def test_stage_entities_batch_bulk_io():
    entities = [
        {"entity_id": "000001", "start_date": "20250101", "end_date": "20250110"},
        {"entity_id": "000002", "start_date": "20250101", "end_date": "20250110"},
    ]
    settings = {
        "data": {
            "required": [
                {"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}},
            ]
        }
    }
    mock_dm = MagicMock()
    mock_dm.stock.kline.load_batch.return_value = {
        "000001": [{"date": "20250102", "close": 1.0}],
        "000002": [{"date": "20250103", "close": 2.0}],
    }

    with patch(
        "core.modules.tag.engines.shared.staging.batch_stage.fetch_prior_tag_values_batch",
        return_value={"000001": {"1": "true"}, "000002": {"1": "false"}},
    ):
        out = stage_entities_batch(
            data_mgr=mock_dm,
            entities=entities,
            settings=settings,
            tag_definition_ids=[1],
        )

    mock_dm.stock.kline.load_batch.assert_called_once()
    assert set(out.keys()) == {"000001", "000002"}
    assert out["000001"]["prior_tag_values"]["1"] == "true"
    assert "stock.kline.daily" in out["000001"]["slot_data"]


def test_stage_entities_batch_moneyflow_only():
    entities = [
        {"entity_id": "000019.SZ", "start_date": "20250101", "end_date": "20250110"},
    ]
    settings = {
        "data": {
            "required": [
                {"data_id": "stock.moneyflow.daily", "params": {}},
            ]
        }
    }
    from core.modules.data_manager import DataManager

    dm = DataManager(is_verbose=False)
    out = stage_entities_batch(
        data_mgr=dm,
        entities=entities,
        settings=settings,
        tag_definition_ids=[8],
    )
    eid = "000019.SZ"
    assert eid in out
    assert "stock.moneyflow.daily" in out[eid]["slot_data"]
    assert len(out[eid]["slot_data"]["stock.moneyflow.daily"]) > 0
    assert len(out[eid]["trading_dates"]) > 0
