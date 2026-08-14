"""MatchingService 单元测试。"""

from __future__ import annotations

import pytest

from core.modules.market_profile.core.services.matching_service import MatchingService

pytestmark = pytest.mark.force_run


class TestMatchingService:
    def test_extract_stock_code(self):
        assert MatchingService.extract_stock_code("000001.SZ") == "000001"
        assert MatchingService.extract_stock_code("688981.SH") == "688981"

    def test_start_with_or(self):
        matching = {"id": {"start_with": ["688"]}}
        assert MatchingService.match_stock_id("688981.SH", matching)
        assert not MatchingService.match_stock_id("600519.SH", matching)

    def test_start_with_multi_or_default(self):
        matching = {"id": {"start_with": ["43", "83", "87"]}}
        assert MatchingService.match_stock_id("830001.BJ", matching)

    def test_relation_or_explicit(self):
        matching = {
            "id": {"start_with": ["43", "83"], "relation": "or"},
        }
        assert MatchingService.match_stock_id("430001.BJ", matching)
