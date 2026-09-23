"""SampleListResolver：sampling → to_sample_list → sorted unique。"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Sequence

import pytest

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.hook_params import StrategyContext
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.entity_loader.sample_list_resolver import (
    SampleListResolver,
)

pytestmark = pytest.mark.force_run


def _settings(raw=None) -> StrategySettings:
    return StrategySettings.to_usable(raw or {})


def _info(**kwargs: Any) -> SimpleNamespace:
    base = {
        "key": "demo/x",
        "unique_relative_path": "demo/x",
        "hooks_module_path": "",
        "hooks_class": None,
        "strategy_file": "",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class _FilterHooks(StrategyHooks):
    def to_sample_list(
        self, ctx: StrategyContext, stock_list: Sequence[str]
    ) -> Sequence[str]:
        _ = ctx
        return [sid for sid in stock_list if sid.endswith(".SZ")] + ["ghost.SH"]

    def has_opportunity(self, ctx: StrategyContext) -> bool:
        _ = ctx
        return False


def test_normalize_ids_dedupes_and_strips() -> None:
    assert SampleListResolver._normalize_ids(
        [" 000002.SZ ", "", "000001.SZ", "000002.SZ"]
    ) == ["000002.SZ", "000001.SZ"]


def test_resolve_without_sampling_sorts_when_hooks_missing() -> None:
    out = SampleListResolver.resolve(
        _info(),
        _settings(),
        universe=["000002.SZ", "000001.SZ", "000001.SZ"],
    )
    assert out == ["000001.SZ", "000002.SZ"]


def test_resolve_applies_uniform_sampling_then_sorts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        SampleListResolver,
        "_apply_hook",
        classmethod(lambda cls, si, s, sl: list(sl)),
    )
    settings = _settings(
        {
            "sampling": {
                "use_sampling": True,
                "strategy": "uniform",
                "sampling_amount": 2,
            }
        }
    )
    universe = [f"{i:06d}.SZ" for i in range(1, 6)]
    out = SampleListResolver.resolve(_info(), settings, universe=universe)
    assert out == sorted(["000001.SZ", "000003.SZ"])


def test_apply_hook_intersects_and_drops_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    runtime = StrategyHookRuntime(
        _FilterHooks(),
        strategy_name="demo/x",
        settings=settings,
    )
    monkeypatch.setattr(
        StrategyHookRuntime,
        "from_strategy_info",
        classmethod(lambda cls, si, s: (runtime, None)),
    )
    out = SampleListResolver._apply_hook(
        _info(),
        settings,
        ["000001.SZ", "600000.SH", "000002.SZ"],
    )
    assert out == ["000001.SZ", "000002.SZ"]


def test_resolve_sampling_then_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        {
            "sampling": {
                "use_sampling": True,
                "strategy": "uniform",
                "sampling_amount": 3,
            }
        }
    )
    runtime = StrategyHookRuntime(
        _FilterHooks(),
        strategy_name="demo/x",
        settings=settings,
    )
    monkeypatch.setattr(
        StrategyHookRuntime,
        "from_strategy_info",
        classmethod(lambda cls, si, s: (runtime, None)),
    )
    # uniform amount=3 on 5 → indices 0,2,4 → 000001/000003/000005.SZ；hook 全是 .SZ
    out = SampleListResolver.resolve(
        _info(),
        settings,
        universe=[f"{i:06d}.SZ" for i in range(1, 6)] + ["600000.SH"],
    )
    assert out == ["000001.SZ", "000003.SZ", "000005.SZ"]
