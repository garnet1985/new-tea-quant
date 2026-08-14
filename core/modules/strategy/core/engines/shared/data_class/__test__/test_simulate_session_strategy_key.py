"""SimulateSession.strategy_key prefers meta.key over folder path."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.modules.strategy.core.engines.shared.data_class.simulate_session import (
    SimulateSession,
)
from core.modules.strategy.core.enums import SimulateKind


def test_simulate_session_strategy_key_prefers_meta_key():
    info = MagicMock()
    info.key = "rsi_v3"
    info.unique_relative_path = "demo/regression/rsi/rsi_v3_pe_percentile_gate"
    fp = MagicMock()
    session = SimulateSession(
        strategy_info=info,
        fp_res=fp,
        kind=SimulateKind.ENUMERATE,
    )
    assert session.strategy_key == "rsi_v3"


def test_simulate_session_strategy_key_falls_back_to_path():
    info = MagicMock()
    info.key = ""
    info.unique_relative_path = "demo/legacy"
    fp = MagicMock()
    session = SimulateSession(
        strategy_info=info,
        fp_res=fp,
        kind=SimulateKind.ENUMERATE,
    )
    assert session.strategy_key == "demo/legacy"
