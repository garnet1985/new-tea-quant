"""CalendarSlice / Opportunities 轻量快捷。"""

from __future__ import annotations

import pytest

from core.modules.strategy.core.engines.shared.data_class import Opportunity, StockInfo
from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    OpportunityMeta,
)
from core.modules.strategy.core.hooks.hook_params import CalendarSlice, Opportunities

pytestmark = pytest.mark.force_run


def test_calendar_slice_light_helpers() -> None:
    calendar_slice = CalendarSlice(
        flags={"as_of_date": "20240110", "is_period_start": True},
        base_data_key="k",
        loader=lambda: {
            "000001.SZ": {"k": [{"date": "20240110", "close": 11}]},
            "000002.SZ": {"k": [{"date": "20240110", "close": 22}]},
        },
    )
    assert calendar_slice.as_of == "20240110"
    assert "as_of_date" not in calendar_slice.flags
    assert len(calendar_slice) == 2
    assert calendar_slice.count == 2
    assert calendar_slice.has("000001.SZ") is True
    assert calendar_slice.has("missing") is False
    closes = [rec.latest["close"] for rec in calendar_slice.iter_records()]
    assert closes == [11, 22]


def test_opportunities_light_helpers() -> None:
    items = [
        Opportunity(
            stock=StockInfo(id="AAA"),
            record_of_today={},
            meta=OpportunityMeta(opportunity_id="1"),
        ),
        Opportunity(
            stock=StockInfo(id="BBB"),
            record_of_today={},
            meta=OpportunityMeta(opportunity_id="2"),
        ),
        Opportunity(
            stock=StockInfo(id="CCC"),
            record_of_today={},
            meta=OpportunityMeta(opportunity_id="3"),
        ),
    ]
    opps = Opportunities(
        items,
        account={"held_entity_ids": ["BBB"], "remaining_slots": 2},
    )
    assert opps.remaining_slots == 2
    assert opps.held_ids == frozenset({"BBB"})
    assert opps.is_held("BBB") is True
    assert opps.is_held("AAA") is False
    assert opps.entities() == ["AAA", "BBB", "CCC"]
    assert [Opportunities.entity_id(x) for x in opps.head(2)] == ["AAA", "BBB"]
    assert [Opportunities.entity_id(x) for x in opps.exclude_held()] == ["AAA", "CCC"]
    assert opps.head(0) == []
