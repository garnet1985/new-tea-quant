from core.tables.stock.stock_st_periods.st_period_rules import (
    TIER_ST,
    TIER_STAR_ST,
    merge_periods_to_tiers,
)


def test_merge_st_and_sst_into_st_tier():
    raw = [
        {"st_level": "ST", "start_date": "20200101", "end_date": "20200630"},
        {"st_level": "SST", "start_date": "20200701", "end_date": "20201231"},
    ]
    tiers = merge_periods_to_tiers(raw)
    assert len(tiers[TIER_ST]) == 1
    assert tiers[TIER_ST][0]["start_date"] == "20200101"
    assert tiers[TIER_ST][0]["end_date"] == "20201231"
    assert tiers[TIER_STAR_ST] == []


def test_merge_star_st_levels():
    raw = [
        {"st_level": "STAR_ST", "start_date": "20210101", "end_date": "20210301"},
        {"st_level": "S_STAR_ST", "start_date": "20210401", "end_date": "20210601"},
    ]
    tiers = merge_periods_to_tiers(raw)
    assert len(tiers[TIER_STAR_ST]) == 2
    assert tiers[TIER_ST] == []
