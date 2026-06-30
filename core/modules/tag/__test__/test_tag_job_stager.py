from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.tag.engines.shared.staging.job_stager import TagJobStager, TagStageJob


def test_tag_job_stager_builds_inline_inject_payload():
    job = TagStageJob(
        job_id="scenario_000001",
        payload={
            "entity_id": "000001",
            "entity_type": "stock",
            "scenario_name": "demo",
            "update_mode": "full_refresh",
            "start_date": "20250101",
            "end_date": "20250102",
            "tag_definitions": [{"tag_name": "t1"}],
            "settings": {"name": "demo"},
            "worker_module_path": "mod.worker",
            "worker_class_name": "DemoWorker",
            "global_extra_cache": {},
        },
    )

    mock_tdm = MagicMock()
    mock_tdm.get_trading_dates.return_value = ["20250101", "20250102"]
    mock_tdm.get_slot_data.return_value = {
        "stock.kline.daily": [{"date": "20250101", "close": 1.0}],
    }
    mock_tdm.get_time_field_overrides.return_value = {"stock.kline.daily": "date"}

    with patch(
        "core.modules.tag.engines.shared.staging.job_stager.TagDataManager",
        return_value=mock_tdm,
    ), patch(
        "core.modules.tag.engines.shared.staging.job_stager.fetch_prior_tag_values",
        return_value={"1": '{"value": true}'},
    ):
        stager = TagJobStager(data_mgr=MagicMock())
        enriched = stager.stage_job(job)

    mock_tdm.hydrate_row_slots.assert_called_once_with("20250101", "20250102")
    inject = enriched.payload["_inject"]
    assert inject["trading_dates"] == ["20250101", "20250102"]
    assert inject["slot_data"]["stock.kline.daily"] == [{"date": "20250101", "close": 1.0}]
    assert inject["prior_tag_values"] == {"1": '{"value": true}'}


def test_tag_job_stager_batch_preserves_worker_file_path():
    job = TagStageJob(
        job_id="scenario_batch",
        payload={
            "entity_type": "stock_kline_daily",
            "scenario_name": "demo/market_cap_tier",
            "update_mode": "incremental",
            "tag_definitions": [{"id": 1, "tag_name": "market_cap_tier"}],
            "settings": {"name": "demo/market_cap_tier"},
            "worker_module_path": "_ntq_tag_worker_demo_market_cap_tier",
            "worker_class_name": "MarketCapTierTagWorker",
            "worker_file_path": "/tmp/demo/market_cap_tier/tag_worker.py",
            "global_extra_cache": {},
            "entities": [
                {"entity_id": "000001.SZ", "start_date": "20250101", "end_date": "20250102"},
                {"entity_id": "000002.SZ", "start_date": "20250101", "end_date": "20250102"},
            ],
        },
    )

    with patch(
        "core.modules.tag.engines.shared.staging.job_stager.stage_entities_batch",
        return_value={
            "000001.SZ": {"slot_data": {}, "trading_dates": [], "prior_tag_values": {}},
            "000002.SZ": {"slot_data": {}, "trading_dates": [], "prior_tag_values": {}},
        },
    ):
        stager = TagJobStager(data_mgr=MagicMock())
        enriched = stager.stage_job(job)

    assert enriched.payload["worker_file_path"] == "/tmp/demo/market_cap_tier/tag_worker.py"
    assert enriched.payload["_inject"]["by_entity"]["000001.SZ"] is not None

