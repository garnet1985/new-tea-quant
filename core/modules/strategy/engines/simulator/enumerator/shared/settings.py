#!/usr/bin/env python3
"""
Opportunity Enumerator Settings
"""

from dataclasses import dataclass, field
from typing import Any, Dict

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)


@dataclass
class EnumeratorSettings:
    strategy_name: str
    raw: Dict[str, Any]
    data: Dict[str, Any] = field(init=False)
    price_simulator: Dict[str, Any] = field(init=False)
    goal: Dict[str, Any] = field(init=False)
    use_sampling: bool = field(init=False)
    max_workers: "str | int" = field(init=False)
    min_required_records: int = field(init=False)
    is_verbose: bool = field(init=False)

    def __post_init__(self) -> None:
        self._normalize_views()

    @classmethod
    def from_raw(cls, strategy_name: str, settings_dict: Dict[str, Any]) -> "EnumeratorSettings":
        return cls(strategy_name=strategy_name, raw=settings_dict)

    @classmethod
    def from_base(cls, base_settings: StrategySettingsView) -> "EnumeratorSettings":
        return cls(strategy_name=base_settings.name, raw=base_settings.to_dict())

    def _normalize_views(self) -> None:
        settings = self.raw or {}
        data = dict(settings.get("data") or {})
        brd = data.get("base_required_data")
        if isinstance(brd, dict) and brd.get("params") is None:
            brd["params"] = {}

        mrr = data.get("min_required_records", 100)
        try:
            mrr_int = int(mrr)
        except (TypeError, ValueError):
            mrr_int = 100
        if mrr_int <= 0:
            mrr_int = 100
        data["min_required_records"] = mrr_int
        data.pop("indicators", None)
        brd_ind = brd.get("indicators") if isinstance(brd, dict) else None
        if isinstance(brd, dict) and brd_ind is None:
            brd["indicators"] = {}
        extra_sources = data.get("extra_required_data_sources")
        if extra_sources is None:
            extra_sources = []
        for item in extra_sources:
            if isinstance(item, dict) and item.get("indicators") is None:
                item["indicators"] = {}
        data["extra_required_data_sources"] = extra_sources
        self.data = data
        self.min_required_records = mrr_int

        sampling_block = dict(settings.get("sampling") or {})
        self.use_sampling = bool(sampling_block.get("use_sampling", False))

        enumerator = dict(settings.get("enumerator") or {})
        max_workers = enumerator.get("max_workers", "auto")
        self.max_workers = max_workers
        self.is_verbose = bool(enumerator.get("is_verbose", False))
        self.calendar_progress_mode = str(
            enumerator.get("calendar_progress_mode") or "open_date"
        ).strip().lower()
        self.entity_progress_mode = str(
            enumerator.get("entity_progress_mode") or "stock"
        ).strip().lower()
        from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
            CalendarSliceRuntimeSettings,
        )

        cs_rt = CalendarSliceRuntimeSettings.from_job_payload({"settings": settings})
        self.calendar_slice_prefetch_enabled = cs_rt.prefetch_enabled
        self.calendar_slice_queue_depth_raw = cs_rt.queue_depth_raw
        self.calendar_slice_reader_workers_raw = cs_rt.reader_workers_raw
        self.calendar_slice_queue_depth = cs_rt.queue_depth
        self.calendar_slice_reader_workers = cs_rt.reader_workers

        simulator = dict(settings.get("price_simulator") or {})
        raw_goal = settings.get("goal")
        goal = raw_goal if isinstance(raw_goal, dict) else {}
        self.price_simulator = simulator
        self.goal = goal

    def to_dict(self) -> Dict[str, Any]:
        merged = dict(self.raw or {})
        merged["data"] = self.data
        merged["price_simulator"] = self.price_simulator
        if "sampling" not in merged or not isinstance(merged.get("sampling"), dict):
            merged["sampling"] = {}
        merged["sampling"] = dict(merged["sampling"])
        merged["sampling"]["use_sampling"] = self.use_sampling
        if "enumerator" not in merged:
            merged["enumerator"] = {}
        merged["enumerator"].pop("use_sampling", None)
        merged["enumerator"].pop("max_test_versions", None)
        merged["enumerator"]["max_workers"] = self.max_workers
        merged["enumerator"]["is_verbose"] = self.is_verbose
        if self.calendar_progress_mode:
            merged["enumerator"]["calendar_progress_mode"] = self.calendar_progress_mode
        if self.entity_progress_mode:
            merged["enumerator"]["entity_progress_mode"] = self.entity_progress_mode
        merged["enumerator"]["calendar_slice"] = {
            "queue_depth": self.calendar_slice_queue_depth_raw,
            "prefetch_enabled": self.calendar_slice_prefetch_enabled,
            "reader_workers": self.calendar_slice_reader_workers_raw,
        }
        return merged
