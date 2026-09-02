"""Strategy.simulate 指纹缓存编排：hit / miss / 补跑 enum / 磁盘 registry。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import core.modules.strategy.core.strategy as strategy_module
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.engines.enumerator.pipeline import EnumeratorPipeline
from core.modules.strategy.core.engines.shared.data_class.simulate_session import (
    SimulateSession,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.strategy import Strategy


def _prepare_entity_cache(self, **kwargs):
    self.global_entity_cache = MagicMock()
    return self.global_entity_cache


def _fps():
    return SimpleNamespace(
        execute_fp="sfp",
        env_fp="efp",
        disk_settings_hash="dsh",
        settings_diff={},
        effective_settings=StrategySettings.from_dict({"core": {"n": 1}}),
        entity_ids=[],
    )


def _ctx(*, kind=SimulateKind.PRICE_FACTOR):
    info = MagicMock()
    info.id.return_value = "demo/rsi"
    info.relative_path = "demo/rsi"
    return SimulateSession(
        strategy_info=info,
        fp_res=_fps(),
        kind=kind,
        global_entity_cache=MagicMock(),
    )


def test_resolve_steps_price_ignore_cache_skips_enum_reuse():
    ctx = _ctx()
    with patch.object(
        EnumeratorPipeline,
        "find_output_version_via_fps",
        return_value="7",
    ):
        Strategy._resolve_steps(ctx, ignore_cache=True)
    assert ctx.steps == [SimulateKind.ENUMERATE, SimulateKind.PRICE_FACTOR]
    assert ctx.enum_version is None


def test_resolve_steps_price_reuses_enum_version():
    ctx = _ctx()
    with patch.object(
        EnumeratorPipeline,
        "find_output_version_via_fps",
        return_value="7",
    ):
        Strategy._resolve_steps(ctx)
    assert ctx.steps == [SimulateKind.PRICE_FACTOR]
    assert ctx.enum_version == "7"


def test_resolve_steps_price_prepends_enumerate_when_missing():
    ctx = _ctx()
    with patch.object(
        EnumeratorPipeline,
        "find_output_version_via_fps",
        return_value=None,
    ):
        Strategy._resolve_steps(ctx)
    assert ctx.steps == [SimulateKind.ENUMERATE, SimulateKind.PRICE_FACTOR]
    assert ctx.enum_version is None


def test_simulate_returns_price_slot_on_cache_hit():
    info = MagicMock()
    info.id.return_value = "demo/rsi"
    info.relative_path = "demo/rsi"
    cached = {"price_factor": {"version_id": 9, "success": True}}

    with patch.object(
        strategy_module.DiscoveryService,
        "find_strategy",
        return_value=info,
    ), patch.object(
        strategy_module.DiscoveryService,
        "resolve_strategy_folder",
        return_value=Path("/tmp/demo"),
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_stock_list",
        return_value=[],
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_latest_completed_trading_date",
        return_value="2024-01-01",
    ), patch.object(
        strategy_module.FingerprintCalculator,
        "calculate_fingerprints",
        return_value=_fps(),
    ), patch.object(
        strategy_module.SimulationVersionStore,
        "get_cache",
        return_value=cached,
    ) as get_cache, patch.object(
        Strategy,
        "_run_steps",
    ) as run_steps:
        out = Strategy.simulate("demo/rsi", kind=SimulateKind.PRICE_FACTOR)

    assert out["price_factor"] == cached["price_factor"]
    assert out["version_id"] == "9"
    get_cache.assert_called_once()
    run_steps.assert_not_called()


def test_resolve_steps_enumerate_is_single_step() -> None:
    ctx = _ctx(kind=SimulateKind.ENUMERATE)
    Strategy._resolve_steps(ctx)
    assert ctx.steps == [SimulateKind.ENUMERATE]
    assert ctx.enum_version is None


def test_strategy_enumerate_delegates_to_simulate() -> None:
    with patch.object(Strategy, "simulate", return_value={"ok": True}) as sim:
        out = Strategy.enumerate("demo/rsi", ignore_cache=True, runtime_settings={"a": 1})
    assert out == {"ok": True}
    sim.assert_called_once_with(
        "demo/rsi",
        kind=SimulateKind.ENUMERATE,
        ignore_cache=True,
        runtime_settings={"a": 1},
    )


def test_simulate_missing_strategy_raises() -> None:
    with patch.object(strategy_module.DiscoveryService, "find_strategy", return_value=None):
        with pytest.raises(ValueError, match="不存在或未启用"):
            Strategy.simulate("missing", kind=SimulateKind.ENUMERATE)


def test_simulate_enumerate_cache_miss_runs_enumerator_pipeline() -> None:
    """Facade 主线：cache miss → Pipeline.run → 写磁盘 registry。"""
    info = MagicMock()
    info.id.return_value = "demo/rsi"
    info.unique_relative_path = "demo/rsi"
    info.key = "demo/rsi"
    info.relative_path = "demo/rsi"
    step_res = {
        "success": True,
        "version_id": "3",
        "output_dir": "/tmp/demo/simulations/3/enum",
        "opportunities_count": 0,
    }

    with patch.object(
        strategy_module.DiscoveryService,
        "find_strategy",
        return_value=info,
    ), patch.object(
        strategy_module.DiscoveryService,
        "resolve_strategy_folder",
        return_value=Path("/tmp/demo"),
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_stock_list",
        return_value=["000001.SZ"],
    ), patch.object(
        strategy_module.GlobalEntityCache,
        "get_latest_completed_trading_date",
        return_value="20240110",
    ), patch.object(
        strategy_module.FingerprintCalculator,
        "calculate_fingerprints",
        return_value=_fps(),
    ), patch.object(
        strategy_module.SimulationVersionStore,
        "get_cache",
        return_value=None,
    ), patch.object(
        SimulateSession,
        "prepare_entity_cache",
        _prepare_entity_cache,
    ), patch.object(
        EnumeratorPipeline,
        "run",
        return_value=step_res,
    ) as run, patch.object(
        strategy_module.SimulationVersionStore,
        "record_step_complete",
    ) as record:
        out = Strategy.simulate("demo/rsi", kind=SimulateKind.ENUMERATE)

    assert out["enumerate"]["version_id"] == "3"
    assert out["version_id"] == "3"
    run.assert_called_once()
    record.assert_called_once()
    assert record.call_args.kwargs["full_settings"]["core"]["n"] == 1
    assert record.call_args.kwargs["effective_settings"]["core"]["n"] == 1
    assert record.call_args.kwargs["kind"] == SimulateKind.ENUMERATE
    assert record.call_args.kwargs["version_id"] == "3"


def test_simulate_session_validate_for_run_requires_steps() -> None:
    ctx = _ctx(kind=SimulateKind.ENUMERATE)
    with pytest.raises(ValueError, match="steps"):
        ctx.validate_for_run()
