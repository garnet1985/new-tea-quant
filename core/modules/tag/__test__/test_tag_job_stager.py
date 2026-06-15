from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.infra.job_pipeline.types import Job
from core.modules.tag.components.job_staging.tag_job_stager import TagJobStager


def test_tag_job_stager_builds_inline_inject_payload():
    job = Job(
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
        "core.modules.tag.components.job_staging.tag_job_stager.TagDataManager",
        return_value=mock_tdm,
    ), patch(
        "core.modules.tag.components.job_staging.tag_job_stager.fetch_prior_tag_values",
        return_value={"1": '{"value": true}'},
    ):
        stager = TagJobStager(data_mgr=MagicMock())
        enriched = stager.stage_job(job)

    mock_tdm.hydrate_row_slots.assert_called_once_with("20250101", "20250102")
    inject = enriched.payload["_inject"]
    assert inject["trading_dates"] == ["20250101", "20250102"]
    assert inject["slot_data"]["stock.kline.daily"] == [{"date": "20250101", "close": 1.0}]
    assert inject["prior_tag_values"] == {"1": '{"value": true}'}
