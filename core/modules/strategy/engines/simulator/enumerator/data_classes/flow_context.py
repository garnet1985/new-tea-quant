#!/usr/bin/env python3
"""Typed flow contexts for opportunity enumerator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.shared.performance_profiler import AggregateProfiler
from core.modules.strategy.services.fingerprint import StrategyRunFingerprint
from .settings import OpportunityEnumeratorSettings


@dataclass
class EnumeratorPreprocessContext:
    strategy_name: str
    enum_settings: Optional[OpportunityEnumeratorSettings] = None
    settings_payload: Optional[Dict[str, Any]] = None
    request_fingerprint: Optional[StrategyRunFingerprint] = None
    result_fingerprint: Optional[StrategyRunFingerprint] = None
    output_dir: Optional[Path] = None
    version_id: Optional[int] = None
    version_dir_name: Optional[str] = None
    jobs: Optional[List[Dict[str, Any]]] = None
    global_extra_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
    max_workers: Optional[int] = None
    start_time: float = 0.0
    aggregate_profiler: Optional[AggregateProfiler] = None


@dataclass
class EnumeratorExecuteContext:
    job_results: Optional[List[Any]] = None


__all__ = ["EnumeratorPreprocessContext", "EnumeratorExecuteContext"]
