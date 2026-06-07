"""JobHelper 单元测试。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.tag.components.helper.job_helper import JobHelper
from core.modules.tag.enums import TagUpdateMode


class TestJobHelper:
    @pytest.mark.parametrize(
        "default_end,expected_end",
        [
            ("20251231", "20250601"),
            (None, "20250601"),
        ],
    )
    def test_refresh_end_date_capped_to_latest_completed(self, default_end, expected_end):
        with patch.object(
            JobHelper,
            "_resolve_latest_completed_trading_date",
            return_value="20250601",
        ):
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.REFRESH,
                default_start_date="20200101",
                default_end_date=default_end,
            )
        assert start_date == "20200101"
        assert end_date == expected_end

    def test_incremental_with_last_update_date(self):
        with patch(
            "core.modules.tag.components.helper.job_helper.DateUtils.add_days",
            return_value="20200102",
        ), patch.object(
            JobHelper,
            "_resolve_latest_completed_trading_date",
            return_value="20251231",
        ):
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.INCREMENTAL,
                entity_last_update_date="20200101",
                default_end_date="20201231",
            )
        assert start_date == "20200102"
        assert end_date == "20201231"

    def test_incremental_without_last_update_uses_default_start(self):
        with patch(
            "core.infra.project_context.ConfigManager.get_default_start_date",
            return_value="20200101",
        ), patch.object(
            JobHelper,
            "_resolve_latest_completed_trading_date",
            return_value="20251231",
        ):
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.INCREMENTAL,
                entity_last_update_date=None,
                default_start_date="20200101",
                default_end_date="20201231",
            )
        assert start_date == "20200101"
        assert end_date == "20201231"
