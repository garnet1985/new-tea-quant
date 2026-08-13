"""Strategy.simulate 指纹缓存编排：hit / miss / 补跑 enum / 逐步写 slot。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.strategy import Strategy
from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession


def _fps():
    return SimpleNamespace(
        settings_fp="sfp",
        env_fp="efp",
        disk_settings_hash="dsh",
        settings_diff={},
        effective_settings=SimpleNamespace(),
        entity_ids=[],
        global_entity_cache=MagicMock(),
    )


def _ctx(*, kind=SimulateKind.PRICE_FACTOR):
    info = MagicMock()
    info.id.return_value = "demo/rsi"
    info.relative_path = "demo/rsi"
    return SimulateSession(strategy_info=info, fp_res=_fps(), kind=kind)


def test_resolve_steps_price_reuses_enum_version():
    ctx = _ctx()
    with patch(
        "core.modules.strategy.core.engines.enumerator.EnumeratorPipeline"
        ".find_output_version_via_fps",
        return_value="7",
    ):
        Strategy._resolve_steps(ctx)
    assert ctx.steps == [SimulateKind.PRICE_FACTOR]
    assert ctx.enum_version == "7"


def test_resolve_steps_price_prepends_enumerate_when_missing():
    ctx = _ctx()
    with patch(
        "core.modules.strategy.core.engines.enumerator.EnumeratorPipeline"
        ".find_output_version_via_fps",
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

    with patch(
        "core.modules.strategy.core.strategy.DiscoveryService.find_strategy",
        return_value=info,
    ), patch(
        "core.modules.strategy.core.strategy.GlobalEntityCache.get_stock_list",
        return_value=[],
    ), patch(
        "core.modules.strategy.core.strategy.GlobalEntityCache"
        ".get_latest_completed_trading_date",
        return_value="2024-01-01",
    ), patch(
        "core.modules.strategy.core.strategy.FingerprintCalculator.calculate_fingerprints",
        return_value=_fps(),
    ), patch(
        "core.modules.strategy.core.strategy.SimulationCacheManager.get_cache",
        return_value=cached,
    ) as get_cache, patch(
        "core.modules.strategy.core.strategy.Strategy._run_steps"
    ) as run_steps:
        out = Strategy.simulate("demo/rsi", kind=SimulateKind.PRICE_FACTOR)

    assert out == cached
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
    with patch(
        "core.modules.strategy.core.strategy.DiscoveryService.find_strategy",
        return_value=None,
    ):
        with pytest.raises(ValueError, match="不存在或未启用"):
            Strategy.simulate("missing", kind=SimulateKind.ENUMERATE)


def test_simulate_enumerate_cache_miss_runs_enumerator_pipeline() -> None:
    """Facade 主线：cache miss → resolve enumerate → Pipeline.run → 写 cache。"""
    info = MagicMock()
    info.id.return_value = "demo/rsi"
    info.unique_relative_path = "demo/rsi"
    info.key = "demo/rsi"
    info.relative_path = "demo/rsi"
    step_res = {"success": True, "version_id": "3", "opportunities_count": 0}

    with patch(
        "core.modules.strategy.core.strategy.DiscoveryService.find_strategy",
        return_value=info,
    ), patch(
        "core.modules.strategy.core.strategy.GlobalEntityCache.get_stock_list",
        return_value=["000001.SZ"],
    ), patch(
        "core.modules.strategy.core.strategy.GlobalEntityCache"
        ".get_latest_completed_trading_date",
        return_value="20240110",
    ), patch(
        "core.modules.strategy.core.strategy.FingerprintCalculator.calculate_fingerprints",
        return_value=_fps(),
    ), patch(
        "core.modules.strategy.core.strategy.SimulationCacheManager.get_cache",
        return_value=None,
    ), patch(
        "core.modules.strategy.core.engines.enumerator.EnumeratorPipeline.run",
        return_value=step_res,
    ) as run, patch(
        "core.modules.strategy.core.strategy.SimulationCacheManager.set_cache",
        return_value=11,
    ) as set_cache:
        out = Strategy.simulate("demo/rsi", kind=SimulateKind.ENUMERATE)

    assert out["enumerate"]["version_id"] == "3"
    assert out["_workbench_version"] == 11
    run.assert_called_once()
    set_cache.assert_called_once()


def test_simulate_session_validate_for_run_requires_steps() -> None:
    ctx = _ctx(kind=SimulateKind.ENUMERATE)
    with pytest.raises(ValueError, match="steps"):
        ctx.validate_for_run()
