#!/usr/bin/env python3
"""Enumerator shared: settings 收集与结果产出。"""

from __future__ import annotations

import importlib
from typing import Any, Tuple

from core.modules.strategy.launcher.run_types import StrategyRunFingerprint

_LAZY = {
    "EnumeratorExecuteContext": (".contexts", "EnumeratorExecuteContext"),
    "EnumeratorPreprocessContext": (".contexts", "EnumeratorPreprocessContext"),
    "EnumeratorProbeContext": (".contexts", "EnumeratorProbeContext"),
    "EnumeratorReport": (".report", "EnumeratorReport"),
    "EnumeratorSettings": (".settings", "EnumeratorSettings"),
    "StrategyEnumeratorSettings": (".strategy_settings", "StrategyEnumeratorSettings"),
}


def __getattr__(name: str) -> Any:
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr = spec
    module = importlib.import_module(module_path, __name__)
    return getattr(module, attr)


__all__ = ["StrategyRunFingerprint", *list(_LAZY.keys())]
