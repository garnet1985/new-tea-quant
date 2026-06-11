#!/usr/bin/env python3
"""StrategyMetaSettings 校验。"""

from core.modules.strategy.engines.shared.data_classes.strategy_settings.meta_settings import (
    StrategyMetaSettings,
)


def test_meta_requires_display_name():
    inst = StrategyMetaSettings.from_raw({"meta": {"display_name": ""}})
    report = inst.validate()
    assert not report.is_usable()


def test_meta_optional_details_entry():
    inst = StrategyMetaSettings.from_raw(
        {
            "meta": {
                "display_name": "RSI",
                "details": {"entry": ["RSI < 20"]},
            }
        }
    )
    report = inst.validate()
    assert report.is_usable()
    assert inst.details is not None
    assert inst.details.entry == ["RSI < 20"]
