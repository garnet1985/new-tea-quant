"""simulation.risk_control.skip_enter_when — settings + price/portfolio 跳过。"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.services.artifacts import (
    EntityInvestmentCsv,
    EnumerateStore,
    InvestmentRow,
)
from core.modules.strategy.core.engines.portfolio.pipeline import PortfolioPipeline
from core.modules.strategy.core.engines.price_factor.executor import PriceFactorJobExecutor
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StatusTagPolicy,
    StrategySettings,
)


def _base_simulation(**risk_overrides):
    return {
        "simulation": {
            "execution": {
                "mode": "entity_based",
            },
            "assumption": {"template": "none"},
            "risk_control": dict(risk_overrides),
        }
    }


def test_skip_enter_when_defaults_empty() -> None:
    settings = StrategySettings.from_dict(_base_simulation())
    settings.apply_defaults()
    assert settings.simulation.risk_control.skip_enter_when.tags == ()
    assert settings.simulation.to_dict()["risk_control"]["skip_enter_when"] == []


def test_skip_enter_when_parses_and_validates() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(skip_enter_when=["st", "star_st", "st"])
    )
    report = settings.validate()
    assert report.is_valid
    assert settings.simulation.risk_control.skip_enter_when.tags == ("st", "star_st")


def test_skip_enter_when_rejects_unknown_tag() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(skip_enter_when=["st", "delisted"])
    )
    report = settings.validate()
    assert not report.is_valid
    assert any(
        "skip_enter_when" in (e.get("field_path") or "") for e in report.errors
    )


def test_match_reason() -> None:
    policy = StatusTagPolicy.from_raw(["star_st"])
    assert policy.match_reason(["st"]) is None
    assert policy.match_reason(["star_st"]) == "stock_status:star_st"
    assert policy.match_reason(["st", "star_st"]) == "stock_status:star_st"
    assert StatusTagPolicy(()).match_reason(["st"]) is None


def _inv_row(**kwargs) -> InvestmentRow:
    base = dict(
        investment_id="1",
        trigger_date="20240101",
        trigger_price=10.0,
        entry_date="20240102",
        entry_price=10.0,
        entry_price_raw=10.0,
        exit_date="20240110",
        exit_price=11.0,
        exit_price_raw=11.0,
        exit_reason="take_profit",
        lifecycle="complete",
        result="win",
        weighted_roi=0.1,
        holding_days=5,
    )
    base.update(kwargs)
    return InvestmentRow(**base)


def test_price_replay_skips_matching_status() -> None:
    rows = [
        _inv_row(investment_id="1", stock_status_at_trigger=("st",)),
        _inv_row(
            investment_id="2",
            entry_date="20240103",
            exit_date="20240108",
            stock_status_at_trigger=(),
        ),
    ]
    out, _ = PriceFactorJobExecutor._replay_entity_investments(
        rows,
        settings=StrategySettings.from_dict(
            _base_simulation(skip_enter_when=["st"])
        ),
    )
    assert [r.opportunity_id for r in out] == ["2"]


def test_portfolio_build_events_skips_matching_status(tmp_path: Path) -> None:
    EnumerateStore.at(tmp_path).write_investments(
        EntityInvestmentCsv(
            entity_id="600000.SH",
            rows=[
                _inv_row(
                    investment_id="1",
                    entry_price_raw=20.0,
                    stock_status_at_trigger=("st",),
                ),
                _inv_row(
                    investment_id="2",
                    entry_date="20240104",
                    exit_date="20240111",
                    entry_price_raw=21.0,
                    stock_status_at_trigger=("star_st",),
                ),
                _inv_row(
                    investment_id="3",
                    entry_date="20240105",
                    exit_date="20240112",
                    entry_price_raw=22.0,
                    stock_status_at_trigger=(),
                ),
            ],
        )
    )

    data = EnumerateStore.hydrate(
        tmp_path,
        entity_ids=["600000.SH"],
        start_date="20240101",
        end_date="20240131",
    )
    events, opps = PortfolioPipeline.build_events(
        data,
        settings=StrategySettings.from_dict(
            _base_simulation(skip_enter_when=["st"])
        ),
    )
    assert sorted(opps.keys()) == ["600000.SH:2", "600000.SH:3"]
    assert {e.investment_id for e in events if e.is_buy()} == {"2", "3"}


class _StatusProvider:
    def __init__(self, tags):
        self._tags = list(tags)

    def status_tags_at(self, entity_id, day):
        _ = entity_id, day
        return list(self._tags)


def test_enumerator_skips_st_opportunity() -> None:
    from core.modules.strategy.core.engines.enumerator.common.state.investment_tracker import (
        InvestmentTracker,
    )
    from core.modules.strategy.core.engines.shared.data_class.opportunity import (
        Opportunity,
        StockInfo,
    )

    tracker = InvestmentTracker(entity_id="600000.SH")
    opp = Opportunity(
        stock=StockInfo(id="600000.SH", name="ST示例"),
        record_of_today={
            "date": "20240102",
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10,
        },
        trigger_date="20240102",
        trigger_price=10.0,
    )
    inv = tracker.register_from_opportunity(
        opp,
        settings=StrategySettings.from_dict(_base_simulation(skip_enter_when=["st"])),
        open_dates=["20240102", "20240103"],
        strategy_name="demo",
        stock_info={"id": "600000.SH", "name": "ST示例"},
        trigger_date="20240102",
        trigger_price=10.0,
        status_tags_provider=_StatusProvider(["st"]),
    )
    assert inv is None
    assert tracker.investment_count() == 0


def test_enumerator_keeps_non_st_when_skip_configured() -> None:
    from core.modules.strategy.core.engines.enumerator.common.state.investment_tracker import (
        InvestmentTracker,
    )
    from core.modules.strategy.core.engines.shared.data_class.opportunity import (
        Opportunity,
        StockInfo,
    )

    tracker = InvestmentTracker(entity_id="600000.SH")
    opp = Opportunity(
        stock=StockInfo(id="600000.SH"),
        record_of_today={
            "date": "20240102",
            "open": 10,
            "high": 11,
            "low": 9,
            "close": 10,
        },
        trigger_date="20240102",
        trigger_price=10.0,
    )
    inv = tracker.register_from_opportunity(
        opp,
        settings=StrategySettings.from_dict(_base_simulation(skip_enter_when=["st"])),
        open_dates=["20240102", "20240103"],
        strategy_name="demo",
        stock_info={"id": "600000.SH"},
        trigger_date="20240102",
        trigger_price=10.0,
        status_tags_provider=_StatusProvider([]),
    )
    assert inv is not None
    assert tracker.investment_count() == 1
