"""Tests for decision BFF implementer wiring."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.bff.APIs.strategy.routes.decision.implementer import (
    StrategyDecisionImplementer,
)


def _engine(**kwargs):
    opp = SimpleNamespace(
        local_id=1,
        entity_id="000001.SZ",
        name="平安银行",
        entry_price_raw=10.0,
        ticker_stats=None,
    )
    defaults = dict(
        dm_id="1",
        version_id="3",
        strategy_key="rsi_v1",
        status="in_progress",
        phase="picking",
        is_completed=False,
        current_date="20250407",
        draft={},
        account=SimpleNamespace(
            cash=1_000_000.0,
            initial_cash=1_000_000.0,
            open_position_count=lambda: 0,
        ),
        allocation=SimpleNamespace(max_portfolio_size=10),
        timeline=SimpleNamespace(asof_stats=lambda _d: None),
        opportunities=lambda: [opp],
        opportunity_by_local=lambda lid: opp if lid == 1 else None,
        holdings=lambda: [],
        info=lambda tokens: {
            "entity_id": "000001.SZ",
            "name": "平安银行",
            "as_of": "20250407",
            "stats": {},
            "ticker_stats": {},
            "columns": ["date"],
            "rows": [],
        },
        set_pick=MagicMock(),
        done=MagicMock(),
        reset=MagicMock(),
        next=MagicMock(
            return_value=SimpleNamespace(
                logs=[
                    SimpleNamespace(
                        date="20250408",
                        entity_id="000001.SZ",
                        name="平安银行",
                        shares=100,
                        profit=10.0,
                        goal_names="win10%",
                        reason="take_profit",
                    )
                ]
            )
        ),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
@patch("core.bff.APIs.strategy.routes.decision.implementer.Strategy.decision_open")
def test_open_session_returns_snapshot(mock_open, _resolve):
    mock_open.return_value = _engine()
    impl = StrategyDecisionImplementer().lazy_load()
    msg = impl.open_session("rsi_v1", new_session=True)
    mock_open.assert_called_once_with(
        "rsi_v1", version_id=None, session_id=None, new_session=True
    )
    assert msg["dm_id"] == "1"
    assert msg["phase"] == "picking"


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
@patch("core.bff.APIs.strategy.routes.decision.implementer.Strategy.decision_list")
def test_list_sessions(mock_list, _resolve):
    mock_list.return_value = {
        "version_id": "3",
        "strategy_key": "rsi_v1",
        "has_portfolio": False,
        "sessions": [],
    }
    impl = StrategyDecisionImplementer().lazy_load()
    msg = impl.list_sessions("rsi_v1", version_id="3")
    mock_list.assert_called_once_with("rsi_v1", version_id="3")
    assert msg["version_id"] == "3"
    assert msg["sessions"] == []
    assert msg["last_session_id"] == ""
    assert msg["has_completed"] is False


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
@patch("core.bff.APIs.strategy.routes.decision.implementer.Strategy.decision_open")
def test_next_includes_exits(mock_open, _resolve):
    mock_open.return_value = _engine()
    impl = StrategyDecisionImplementer().lazy_load()
    msg = impl.next("rsi_v1", "1")
    assert msg["exits"][0]["goal_names"] == "win10%"
    mock_open.return_value.next.assert_called_once_with()


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
@patch("core.bff.APIs.strategy.routes.decision.implementer.Strategy.decision_delete")
def test_delete_session(mock_delete, _resolve):
    mock_delete.return_value = {"ok": True, "dm_id": "1", "version_id": "3"}
    impl = StrategyDecisionImplementer().lazy_load()
    out = impl.delete_session("rsi_v1", "1", version_id="3")
    mock_delete.assert_called_once_with("rsi_v1", "1", version_id="3")
    assert out["ok"] is True


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
def test_get_session_requires_id(_resolve):
    impl = StrategyDecisionImplementer().lazy_load()
    with pytest.raises(ValueError, match="session"):
        impl.get_session("rsi_v1", "  ")


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
@patch("core.bff.APIs.strategy.routes.decision.implementer.Strategy.decision_open")
def test_info_builds_tokens(mock_open, _resolve):
    engine = _engine()
    engine.info = MagicMock(
        return_value={
            "entity_id": "000001.SZ",
            "name": "平安银行",
            "as_of": "20250407",
            "stats": {},
            "ticker_stats": {},
            "columns": ["date"],
            "rows": [],
        }
    )
    mock_open.return_value = engine
    impl = StrategyDecisionImplementer().lazy_load()
    impl.info("rsi_v1", "1", target="1", n=120, columns=["close", "rsi"])
    engine.info.assert_called_once_with(["1", "120", "close,rsi"])


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
@patch("core.bff.APIs.strategy.routes.decision.implementer.Strategy.decision_open")
def test_get_report_requires_completed(mock_open, _resolve):
    mock_open.return_value = _engine(is_completed=False)
    impl = StrategyDecisionImplementer().lazy_load()
    with pytest.raises(ValueError, match="尚未走完"):
        impl.get_report("rsi_v1", "1")


@patch(
    "core.bff.APIs.strategy.routes.decision.implementer.Strategy.resolve",
    return_value="rsi_v1",
)
@patch("core.bff.APIs.strategy.routes.decision.implementer.Strategy.decision_open")
def test_get_report_loads_overall(mock_open, _resolve, tmp_path):
    session_dir = tmp_path / "1"
    session_dir.mkdir()
    (session_dir / "overall_report.json").write_text("{}", encoding="utf-8")
    engine = _engine(is_completed=True)
    engine.store = SimpleNamespace(session_dir=lambda _dm_id: session_dir)
    engine.finalize = MagicMock()
    mock_open.return_value = engine
    loaded = MagicMock()
    loaded.to_ui_dict.return_value = {"capitalMetrics": {"roi": 0.12}}
    impl = StrategyDecisionImplementer().lazy_load()
    with patch(
        "core.modules.strategy.core.engines.portfolio.report_manager.overall_report.OverallReport.load",
        return_value=loaded,
    ), patch(
        "core.bff.APIs.strategy.helpers.portfolio_event_timeline.attach_portfolio_event_timeline",
        side_effect=lambda slot, _dirs: slot,
    ):
        msg = impl.get_report("rsi_v1", "1")
    engine.finalize.assert_not_called()
    assert msg["dm_id"] == "1"
    assert msg["report"]["capitalMetrics"]["roi"] == 0.12
