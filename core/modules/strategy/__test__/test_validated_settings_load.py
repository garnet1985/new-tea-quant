#!/usr/bin/env python3
"""Strategy settings 加载与 market_profile_id 解析。"""

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import resolve_market_profile_id


def test_strategy_settings_validate_unknown_market_profile():
    settings = StrategySettings(
        raw_settings={
            "name": "t",
            "market_profile": "not_a_real_profile_id_zzz",
            "data": {"base_required_data": {"params": {"term": "daily"}}},
            "simulation": {"template": "deterministic"},
        }
    )
    settings.apply_defaults()
    report = settings.validate()
    assert not report.is_usable()


def test_resolve_market_profile_id_prefers_job_payload():
    pid = resolve_market_profile_id(
        {"market_profile_id": "china_a_stock"},
        settings_market_profile="other",
    )
    assert pid == "china_a_stock"


def test_resolve_market_profile_id_falls_back_to_settings():
    pid = resolve_market_profile_id(
        {},
        settings_market_profile="china_a_stock",
    )
    assert pid == "china_a_stock"


def test_capital_rejects_on_insufficient_funds_legacy_key():
    from core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings import (
        StrategyCapitalSimulatorSettings,
    )

    cap = StrategyCapitalSimulatorSettings.from_strategy_root(
        {
            "capital_simulator": {
                "allocation": {"on_insufficient_funds": "skip"},
            }
        }
    )
    report = cap.validate()
    assert report.has_critical_errors()
