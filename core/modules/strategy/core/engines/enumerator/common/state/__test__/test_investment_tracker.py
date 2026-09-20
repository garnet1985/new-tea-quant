"""InvestmentTracker：未完结时不叠第二笔。"""

from core.modules.strategy.core.engines.enumerator.common.state.investment_tracker import (
    InvestmentTracker,
)


def test_register_from_opportunity_skips_when_live():
    tracker = InvestmentTracker(entity_id="000584.SZ")
    tracker.pending_enter.append(object())
    assert tracker.has_live
    assert (
        tracker.register_from_opportunity(
            None,
            settings=None,
            open_dates=(),
            strategy_name="",
            stock_info={},
            trigger_date="20250701",
            trigger_price=0.24,
        )
        is None
    )
    assert tracker._investment_index == 0
