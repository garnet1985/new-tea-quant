"""JobExecutor._replay_entity_investments：锁仓回放。"""
from __future__ import annotations

from core.modules.strategy.core.engines.price_factor.enum_input.investments import (
    InvestmentRow,
)
from core.modules.strategy.core.engines.price_factor.executor import JobExecutor

import pytest

pytestmark = pytest.mark.force_run


def _row(**kwargs) -> InvestmentRow:
    base = dict(
        investment_id="1",
        trigger_date="20240101",
        trigger_price=10.0,
        entry_date="20240102",
        entry_price=10.0,
        exit_date="20240110",
        exit_price=11.0,
        exit_reason="take_profit",
        lifecycle="complete",
        result="win",
        weighted_roi=0.1,
        holding_days=5,
    )
    base.update(kwargs)
    return InvestmentRow(**base)


def test_replay_keeps_non_overlapping() -> None:
    rows = [
        _row(investment_id="1", entry_date="20240102", exit_date="20240105"),
        _row(investment_id="2", entry_date="20240106", exit_date="20240108", weighted_roi=-0.05, result="loss"),
    ]
    out, _ = JobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["1", "2"]


def test_replay_skips_while_locked() -> None:
    rows = [
        _row(investment_id="1", entry_date="20240102", exit_date="20240110"),
        _row(investment_id="2", entry_date="20240105", exit_date="20240108"),
        _row(investment_id="3", entry_date="20240111", exit_date="20240112"),
    ]
    out, _ = JobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["1", "3"]


def test_replay_open_locks_until_backtest_end() -> None:
    rows = [
        _row(
            investment_id="1",
            entry_date="20240102",
            exit_date="",
            exit_price=0.0,
            lifecycle="open",
            result="",
            weighted_roi=0.0,
        ),
        _row(investment_id="2", entry_date="20240601", exit_date="20240602"),
    ]
    out, _ = JobExecutor._replay_entity_investments(rows, backtest_end="20241231")
    assert [r.opportunity_id for r in out] == ["1"]


def test_replay_skips_invalid_entry() -> None:
    rows = [
        _row(investment_id="1", entry_date="", entry_price=0.0),
        _row(investment_id="2", entry_date="20240102", entry_price=10.0),
    ]
    out, _ = JobExecutor._replay_entity_investments(rows)
    assert [r.opportunity_id for r in out] == ["2"]
