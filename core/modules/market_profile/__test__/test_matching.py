#!/usr/bin/env python3
from core.modules.market_profile.rule_engines.shared.matching import (
    extract_stock_code,
    match_stock_id,
)


class TestMatching:
    def test_extract_stock_code(self):
        assert extract_stock_code("000001.SZ") == "000001"
        assert extract_stock_code("688981.SH") == "688981"

    def test_start_with_or(self):
        matching = {"id": {"start_with": ["688"]}}
        assert match_stock_id("688981.SH", matching)
        assert not match_stock_id("600519.SH", matching)

    def test_start_with_multi_or_default(self):
        matching = {"id": {"start_with": ["43", "83", "87"]}}
        assert match_stock_id("830001.BJ", matching)

    def test_relation_or_explicit(self):
        matching = {
            "id": {"start_with": ["43", "83"], "relation": "or"},
        }
        assert match_stock_id("430001.BJ", matching)
