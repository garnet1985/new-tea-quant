"""Slice mode config: load calendar_slice dispatch from worker.json."""
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple
from core.modules.backtest_engine.core.shared.machine_info import (
    MachineCapacity,
    MachineInfo,
)
from core.modules.backtest_engine.core.shared.worker_json import (
    resolve_executor_section,
)

logger = logging.getLogger(__name__)

DEFAULT_SLICE_OPEN_DAYS: int = 20
DEFAULT_PRELOAD_DEPTH: int = 2

# executor_key → (job_pipeline profile, calendar_slice section)
_EXECUTOR_DISPATCH_PROFILES: Dict[str, Tuple[str, str]] = {
    "tag": ("tag", "calendar_slice"),
    "strategy.enum": ("enumerator", "calendar_slice"),
}


class SliceConfig:
    """Slice mode config (reader + compute dispatch from worker.json)."""

    @staticmethod
    def resolve_dispatch_performance(executor_key: str) -> Dict[str, Any]:
        """
        Load calendar_slice dispatch config from worker.json.

        Args:
            executor_key: Probe / worker id (``tag``, ``strategy.enum``, ...).

        Returns:
            Dispatch performance dict for planner / executor.
        """
        performance = resolve_executor_section(
            executor_key,
            _EXECUTOR_DISPATCH_PROFILES,
            defaults={
                "reader_workers": "auto",
                "queue_depth": "auto",
                "prefetch_enabled": True,
            },
            setdefaults={
                "slice_open_days": "auto",
                "reader_workers": "auto",
                "queue_capacity": "auto",
                "preload_depth": "auto",
                "compute_processes": 1,
            },
        )
        SliceConfig._normalize_worker_fields(performance)
        logger.debug(
            "slice dispatch config loaded: executor=%s keys=%s",
            executor_key,
            sorted(performance),
        )
        return performance

    @staticmethod
    def normalize_for_planning(
        performance: Dict[str, Any],
        capacity: MachineCapacity,
        *,
        dispatch_slices: int,
    ) -> Dict[str, Any]:
        """Resolve ``auto`` fields before planner / OOM logic."""
        settings = dict(performance)
        SliceConfig._normalize_worker_fields(settings)

        if settings.get("slice_open_days") in (None, "", "auto"):
            settings["slice_open_days"] = DEFAULT_SLICE_OPEN_DAYS

        available_workers = MachineInfo.get_available_workers(capacity)
        if settings.get("reader_workers") in (None, "", "auto"):
            # Reserve one core for compute lane in the orchestrator subprocess.
            settings["reader_workers"] = max(1, available_workers - 1)

        if settings.get("preload_depth") in (None, "", "auto"):
            prefetch_enabled = settings.get("prefetch_enabled", True)
            settings["preload_depth"] = (
                DEFAULT_PRELOAD_DEPTH if prefetch_enabled else 1
            )

        preload_depth = int(settings["preload_depth"])
        if settings.get("queue_capacity") in (None, "", "auto"):
            reader_workers = int(settings["reader_workers"])
            settings["queue_capacity"] = max(preload_depth * 2, reader_workers)

        if settings.get("compute_processes") in (None, "", "auto"):
            settings["compute_processes"] = 1

        SliceConfig._validate_resolved(settings)
        return settings

    @staticmethod
    def _normalize_worker_fields(settings: Dict[str, Any]) -> None:
        """Map worker.json calendar_slice keys to planner field names."""
        if "queue_depth" in settings and "queue_capacity" not in settings:
            settings["queue_capacity"] = settings["queue_depth"]
        if "prefetch_enabled" in settings and "preload_depth" not in settings:
            settings["preload_depth"] = (
                DEFAULT_PRELOAD_DEPTH if settings["prefetch_enabled"] else 1
            )

    @staticmethod
    def _validate_resolved(settings: Dict[str, Any]) -> None:
        slice_open_days = int(settings.get("slice_open_days", 0))
        if slice_open_days <= 0:
            raise ValueError(f"slice_open_days must be > 0: {slice_open_days}")

        for field in ("reader_workers", "compute_processes", "queue_capacity", "preload_depth"):
            value = int(settings[field])
            if value <= 0:
                raise ValueError(f"{field} must be > 0: {value}")


__all__ = ["SliceConfig"]
