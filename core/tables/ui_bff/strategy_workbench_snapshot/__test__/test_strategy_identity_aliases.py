"""Workbench snapshot identity: meta.key SSOT + legacy path dual-read."""

from __future__ import annotations

from unittest.mock import patch

from core.tables.ui_bff.strategy_workbench_snapshot.model import (
    SysStrategyWorkbenchSnapshotModel,
)


def test_canonical_strategy_key_prefers_meta_key():
    info = {
        "key": "low_price_v2",
        "unique_relative_path": "demo/cross_sectional/low_price/low_price_all",
        "relative_path": "demo/cross_sectional/low_price/low_price_all",
    }
    with patch(
        "core.modules.strategy.Strategy.find",
        return_value=info,
    ):
        assert (
            SysStrategyWorkbenchSnapshotModel._canonical_strategy_key(
                "demo/cross_sectional/low_price/low_price_all"
            )
            == "low_price_v2"
        )
        assert (
            SysStrategyWorkbenchSnapshotModel._canonical_strategy_key("low_price_v2")
            == "low_price_v2"
        )


def test_identity_aliases_include_key_and_path():
    info = {
        "key": "rsi_v3",
        "unique_relative_path": "demo/regression/rsi/rsi_v3_pe_percentile_gate",
        "relative_path": "demo/regression/rsi/rsi_v3_pe_percentile_gate",
    }
    with patch(
        "core.modules.strategy.Strategy.find",
        return_value=info,
    ):
        aliases = SysStrategyWorkbenchSnapshotModel._identity_aliases("rsi_v3")
    assert aliases[0] == "rsi_v3"
    assert "demo/regression/rsi/rsi_v3_pe_percentile_gate" in aliases


def test_strategy_where_uses_in_for_aliases():
    info = {
        "key": "demo-key",
        "unique_relative_path": "demo/x",
        "relative_path": "demo/x",
    }
    model = SysStrategyWorkbenchSnapshotModel.__new__(SysStrategyWorkbenchSnapshotModel)
    with patch(
        "core.modules.strategy.Strategy.find",
        return_value=info,
    ):
        where, params = model._strategy_where("demo/x")
    assert "IN" in where
    assert params == ("demo/x", "demo-key")
