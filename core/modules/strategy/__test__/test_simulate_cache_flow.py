"""Strategy.simulate 指纹缓存编排：hit / miss / 补跑 enum / 逐步写 slot。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.strategy import Strategy
from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession


def _fps():
    return SimpleNamespace(
        settings_fp="sfp",
        env_fp="efp",
        disk_settings_hash="dsh",
        settings_diff={},
        effective_settings=SimpleNamespace(),
        entity_ids=[],
        global_entity_cache=None,
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


def test_run_steps_writes_each_slot_and_seeds_enum_version():
    ctx = _ctx()
    ctx.steps = [SimulateKind.ENUMERATE, SimulateKind.PRICE_FACTOR]

    enum_res = {"version_id": "3", "success": True}
    price_res = {"version_id": 1, "enum_version_id": "3", "success": True}

    pipe = MagicMock()
    pipe.run.side_effect = [enum_res, price_res]

    with patch(
        "core.modules.strategy.strategy.BackTestPipelines.__class_getitem__",
        return_value=pipe,
    ), patch(
        "core.modules.strategy.strategy.SimulationCacheManager.set_cache"
    ) as set_cache:
        out = Strategy._run_steps(ctx, cache_key="demo/rsi")

    assert out == {
        "enumerate": enum_res,
        "price_factor": price_res,
    }
    assert ctx.enum_version == "3"
    assert set_cache.call_count == 2
    assert set_cache.call_args_list[0].args[2] == {"enumerate": enum_res}
    assert set_cache.call_args_list[1].args[2] == {"price_factor": price_res}


def test_simulate_returns_price_slot_on_cache_hit():
    info = MagicMock()
    info.id.return_value = "demo/rsi"
    info.relative_path = "demo/rsi"
    cached = {"price_factor": {"version_id": 9, "success": True}}

    with patch(
        "core.modules.strategy.strategy.DiscoveryService.find_strategy",
        return_value=info,
    ), patch(
        "core.modules.strategy.strategy.GlobalEntityCache.get_stock_list",
        return_value=[],
    ), patch(
        "core.modules.strategy.strategy.GlobalEntityCache"
        ".get_latest_completed_trading_date",
        return_value="2024-01-01",
    ), patch(
        "core.modules.strategy.strategy.FingerprintCalculator.calculate_fingerprints",
        return_value=_fps(),
    ), patch(
        "core.modules.strategy.strategy.SimulationCacheManager.get_cache",
        return_value=cached,
    ) as get_cache, patch(
        "core.modules.strategy.strategy.Strategy._run_steps"
    ) as run_steps:
        out = Strategy.simulate("demo/rsi", kind=SimulateKind.PRICE_FACTOR)

    assert out == cached
    get_cache.assert_called_once()
    run_steps.assert_not_called()
