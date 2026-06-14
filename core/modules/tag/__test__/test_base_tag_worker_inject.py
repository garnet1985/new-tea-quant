from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.tag.base_tag_worker import BaseTagWorker


class _DummyWorker(BaseTagWorker):
    def calculate_tag(self, as_of_date, historical_data, tag_definition):
        return None


def test_preprocess_uses_inline_inject_without_hydrate():
    inject = {
        "trading_dates": ["20250101"],
        "time_field_overrides": {"stock.kline.daily": "date"},
        "slot_data": {"stock.kline.daily": [{"date": "20250101"}]},
    }
    payload = {
        "entity_id": "000001",
        "entity_type": "stock",
        "scenario_name": "demo",
        "update_mode": "full_refresh",
        "start_date": "20250101",
        "end_date": "20250101",
        "tag_definitions": [],
        "settings": {"name": "demo"},
        "_inject": inject,
    }

    mock_tdm = MagicMock()
    with patch(
        "core.modules.tag.components.data_management.tag_data_manager.TagDataManager",
        return_value=mock_tdm,
    ):
        worker = _DummyWorker(payload)
        worker._preprocess()

    mock_tdm.apply_injected_bundle.assert_called_once()
    mock_tdm.hydrate_row_slots.assert_not_called()
    assert worker.trading_dates == ["20250101"]
    assert worker.data_mgr is None
