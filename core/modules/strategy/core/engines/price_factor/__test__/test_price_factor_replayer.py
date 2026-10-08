"""PriceFactorJobExecutor._replay_entity_investments：去噪并行回放。"""
from __future__ import annotations

from core.modules.strategy.core.engines.price_factor.executor import PriceFactorJobExecutor
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.hook_params import StrategyContext
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    CompletedGoal,
    EnumResult,
)

import pytest

pytestmark = pytest.mark.force_run


def _row(**kwargs) -> EnumResult:
    base = dict(
        investment_id="1",
        trigger_date="20240101",
        trigger_price=10.0,
        entry_date="20240102",
        entry_price=10.0,
        entry_price_hfq=10.0,
        exit_date="20240110",
        exit_price=11.0,
        exit_price_hfq=11.0,
        exit_reason="take_profit",
        lifecycle="complete",
        result="win",
        weighted_roi=0.1,
        holding_days=5,
    )
    base.update(kwargs)
    if "entry_price_hfq" not in kwargs:
        base["entry_price_hfq"] = float(base.get("entry_price") or 0.0)
    if "exit_price_hfq" not in kwargs:
        base["exit_price_hfq"] = float(base.get("exit_price") or 0.0)
    return EnumResult(**base)


def test_replay_keeps_non_overlapping() -> None:
    rows = [
        _row(investment_id="1", trigger_date="20240102", entry_date="20240102", exit_date="20240105"),
        _row(
            investment_id="2",
            trigger_date="20240106",
            entry_date="20240106",
            exit_date="20240108",
            weighted_roi=-0.05,
            result="loss",
        ),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["1", "2"]


def test_replay_merges_adjacent_triggers() -> None:
    rows = [
        _row(investment_id="1", trigger_date="20240201", entry_date="20240201", exit_date="20240210"),
        _row(investment_id="2", trigger_date="20240202", entry_date="20240202", exit_date="20240208"),
        _row(investment_id="3", trigger_date="20240203", entry_date="20240203", exit_date="20240209"),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["1"]


def test_replay_keeps_distant_episodes_in_parallel() -> None:
    rows = [
        _row(investment_id="1", trigger_date="20240201", entry_date="20240201", exit_date="20240501"),
        _row(investment_id="2", trigger_date="20240202", entry_date="20240202", exit_date="20240208"),
        _row(investment_id="3", trigger_date="20240401", entry_date="20240401", exit_date="20240410"),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["1", "3"]


def test_replay_open_first_does_not_block_later_episode() -> None:
    rows = [
        _row(
            investment_id="1",
            trigger_date="20240102",
            entry_date="20240102",
            exit_date="",
            exit_price=0.0,
            lifecycle="open",
            result="",
            weighted_roi=0.0,
        ),
        _row(investment_id="2", trigger_date="20240601", entry_date="20240601", exit_date="20240602"),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(rows, backtest_end="20241231")
    assert [r.opportunity_id for r in out] == ["1", "2"]


def test_replay_skips_invalid_entry() -> None:
    rows = [
        _row(investment_id="1", entry_date="", entry_price=0.0),
        _row(investment_id="2", entry_date="20240102", entry_price=10.0),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["2"]


def test_replay_uses_enum_hfq_roi_not_qfq_split() -> None:
    """10 送 10：qfq 腰斩、hfq 持平 → price 层 roi 必须是 0，不能是 −50%。"""
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            entry_price=10.0,
            exit_date="20240110",
            exit_price=5.0,
            entry_price_hfq=10.0,
            exit_price_hfq=10.0,
            exit_reason="expiration",
            weighted_roi=0.0,
            result="win",
        )
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(rows)
    assert len(out) == 1
    assert out[0].lifecycle == "complete"
    assert out[0].roi == pytest.approx(0.0)
    assert out[0].result == "win"
    assert out[0].enter_price == pytest.approx(10.0)
    assert out[0].exit_price == pytest.approx(5.0)
    assert out[0].enter_price_hfq == pytest.approx(10.0)
    assert out[0].exit_price_hfq == pytest.approx(10.0)


def test_replay_enum_result_nested_goals() -> None:
    row = EnumResult(
        investment_id="1",
        entry_date="20240102",
        entry_price=10.0,
        exit_date="20240110",
        exit_price=12.0,
        exit_reason="take_profit",
        weighted_roi=0.15,
        result="win",
        lifecycle="complete",
        completed_goals=(
            CompletedGoal(
                name="take_profit",
                date="20240108",
                price=11.0,
                price_hfq=11.0,
                exit_ratio=0.5,
                reason="take_profit",
            ),
            CompletedGoal(
                name="take_profit",
                date="20240110",
                price=12.0,
                price_hfq=12.0,
                exit_ratio=0.5,
                reason="take_profit",
            ),
        ),
    )
    out, _ = PriceFactorJobExecutor._replay_entity_investments([row])
    assert len(out) == 1
    assert out[0].lifecycle == "complete"
    assert out[0].roi == pytest.approx(0.15)
    assert [goal["date"] for goal in out[0].completed_goals] == ["20240108", "20240110"]
    assert out[0].completed_goals[0]["exit_ratio"] == pytest.approx(0.5)
    assert out[0].completed_goals[1]["goal_name"] == "take_profit"


def _merge_settings(gap: int) -> StrategySettings:
    return StrategySettings.from_dict(
        {
            "simulation": {
                "execution": {"mode": "entity_based"},
                "price": {"opportunity_merge_gap": gap},
            }
        }
    )


def test_replay_merge_gap_zero_keeps_all_days() -> None:
    rows = [
        _row(investment_id="1", trigger_date="20240201", entry_date="20240201", exit_date="20240210"),
        _row(investment_id="2", trigger_date="20240202", entry_date="20240202", exit_date="20240208"),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(
        rows, settings=_merge_settings(0)
    )
    assert [r.opportunity_id for r in out] == ["1", "2"]


def test_replay_limit_up_first_promotes_same_episode() -> None:
    rows = [
        _row(
            investment_id="1",
            trigger_date="20240201",
            entry_date="20240201",
            exit_date="20240205",
            enter_at_limit=True,
        ),
        _row(
            investment_id="2",
            trigger_date="20240202",
            entry_date="20240202",
            exit_date="20240208",
            enter_at_limit=False,
        ),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["2"]


class _AlwaysNewHooks(StrategyHooks):
    def has_opportunity(self, ctx: StrategyContext) -> bool:
        return False

    def is_new_opportunity(self, ctx: StrategyContext) -> bool:
        return True


def test_replay_hook_can_keep_adjacent() -> None:
    rows = [
        _row(investment_id="1", trigger_date="20240201", entry_date="20240201", exit_date="20240210"),
        _row(investment_id="2", trigger_date="20240202", entry_date="20240202", exit_date="20240208"),
    ]
    runtime = StrategyHookRuntime(
        _AlwaysNewHooks(), strategy_name="demo", settings=_merge_settings(1)
    )
    out, _ = PriceFactorJobExecutor._replay_entity_investments(
        rows, settings=_merge_settings(1), hook_runtime=runtime
    )
    assert [r.opportunity_id for r in out] == ["1", "2"]
