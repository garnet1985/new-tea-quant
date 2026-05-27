#!/usr/bin/env python3
"""成交量参与率约束单元测试。"""

from core.modules.strategy.engines.shared.helpers.participation import (
    apply_participation_to_shares,
    bar_volume_shares,
    max_shares_by_participation,
)


def _floor_100(shares: int, _stock_id: str) -> int:
    return (int(shares) // 100) * 100


class TestParticipation:
    def test_bar_volume_shares(self):
        assert bar_volume_shares({"volume": 1_000_000}) == 1_000_000.0
        assert bar_volume_shares({"volume": 0}) is None

    def test_max_shares(self):
        assert max_shares_by_participation(1_000_000, 0.1) == 100_000

    def test_skip_on_exceed(self):
        shares, tag = apply_participation_to_shares(
            200_000,
            bar_volume=1_000_000,
            max_participation_rate=0.1,
            on_exceed="skip",
            floor_shares_fn=_floor_100,
            stock_id="000001.SZ",
        )
        assert shares == 0
        assert tag == "participation_skip"

    def test_clip_on_exceed(self):
        shares, tag = apply_participation_to_shares(
            200_000,
            bar_volume=1_000_000,
            max_participation_rate=0.1,
            on_exceed="clip",
            floor_shares_fn=_floor_100,
            stock_id="000001.SZ",
        )
        assert shares == 100_000
        assert tag == "participation_clipped"

    def test_within_cap_unchanged(self):
        shares, tag = apply_participation_to_shares(
            50_000,
            bar_volume=1_000_000,
            max_participation_rate=0.1,
            on_exceed="clip",
            floor_shares_fn=_floor_100,
            stock_id="000001.SZ",
        )
        assert shares == 50_000
        assert tag is None

    def test_missing_volume_no_limit(self):
        assert max_shares_by_participation(None, 0.1) is None
        shares, tag = apply_participation_to_shares(
            50_000,
            bar_volume=None,
            max_participation_rate=0.1,
            on_exceed="skip",
            floor_shares_fn=_floor_100,
            stock_id="000001.SZ",
        )
        assert shares == 50_000
        assert tag is None
