"""entity_based dispatch 共享解析：clamp / 默认值（唯一 fallback 在 constants.py）。"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from core.infra.job_pipeline.profile.constants import ENUMERATOR_DISPATCH_DEFAULTS


def entities_per_job_bounds(performance: Dict[str, Any]) -> Tuple[int, int]:
    lo = max(1, int(performance.get("entities_per_job_min", ENUMERATOR_DISPATCH_DEFAULTS["entities_per_job_min"])))
    hi = max(lo, int(performance.get("entities_per_job_max", ENUMERATOR_DISPATCH_DEFAULTS["entities_per_job_max"])))
    return lo, hi


def clamp_entities_per_job(n: int, performance: Dict[str, Any]) -> int:
    lo, hi = entities_per_job_bounds(performance)
    return max(lo, min(hi, int(n)))


def default_auto_entities_per_job(performance: Dict[str, Any]) -> int:
    target = int(
        performance.get(
            "entities_per_job_auto_target",
            ENUMERATOR_DISPATCH_DEFAULTS["entities_per_job_auto_target"],
        )
    )
    return clamp_entities_per_job(target, performance)


__all__ = [
    "clamp_entities_per_job",
    "default_auto_entities_per_job",
    "entities_per_job_bounds",
]
