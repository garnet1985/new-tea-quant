#!/usr/bin/env python3
"""Legacy opportunity_enumerator bridges during migration."""

from importlib import import_module

__all__ = [
    "OpportunityEnumeratorSettings",
    "OpportunityEnumeratorWorker",
    "OpportunityEnumerator",
    "PerformanceMetrics",
    "PerformanceProfiler",
]


def __getattr__(name):
    if name == "OpportunityEnumeratorSettings":
        return import_module(
            "core.modules.strategy.components.opportunity_enumerator.enumerator_settings"
        ).OpportunityEnumeratorSettings
    if name == "OpportunityEnumeratorWorker":
        return import_module(
            "core.modules.strategy.components.opportunity_enumerator.enumerator_worker"
        ).OpportunityEnumeratorWorker
    if name == "OpportunityEnumerator":
        return import_module(
            "core.modules.strategy.components.opportunity_enumerator.opportunity_enumerator"
        ).OpportunityEnumerator
    if name in {"PerformanceMetrics", "PerformanceProfiler"}:
        module = import_module(
            "core.modules.strategy.components.opportunity_enumerator.performance_profiler"
        )
        return getattr(module, name)
    raise AttributeError(name)

