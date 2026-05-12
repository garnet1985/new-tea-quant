#!/usr/bin/env python3
"""
Opportunity Enumerator Settings
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Union

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)


@dataclass
class OpportunityEnumeratorSettings:
    strategy_name: str
    raw: Dict[str, Any]
    data: Dict[str, Any] = field(init=False)
    price_simulator: Dict[str, Any] = field(init=False)
    goal: Dict[str, Any] = field(init=False)
    use_sampling: bool = field(init=False)
    max_workers: "str | int" = field(init=False)
    min_required_records: int = field(init=False)
    is_verbose: bool = field(init=False)
    memory_budget_mb: Union[float, str] = field(init=False)
    warmup_batch_size: Union[int, str] = field(init=False)
    min_batch_size: Union[int, str] = field(init=False)
    max_batch_size: Union[int, str] = field(init=False)
    monitor_interval: int = field(init=False)

    def __post_init__(self) -> None:
        self._normalize_views()

    @classmethod
    def from_raw(cls, strategy_name: str, settings_dict: Dict[str, Any]) -> "OpportunityEnumeratorSettings":
        return cls(strategy_name=strategy_name, raw=settings_dict)

    @classmethod
    def from_base(cls, base_settings: StrategySettingsView) -> "OpportunityEnumeratorSettings":
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
        indicators = data.get("indicators")
        if indicators is None:
            indicators = {}
        data["indicators"] = indicators
        extra_sources = data.get("extra_required_data_sources")
        if extra_sources is None:
            extra_sources = []
        data["extra_required_data_sources"] = extra_sources
        self.data = data
        self.min_required_records = mrr_int

        sampling_block = dict(settings.get("sampling") or {})
        self.use_sampling = bool(sampling_block.get("use_sampling", False))

        enumerator = dict(settings.get("enumerator") or {})
        max_output_versions = enumerator.get("max_output_versions", 3)
        try:
            max_output_versions_int = int(max_output_versions)
        except (TypeError, ValueError):
            max_output_versions_int = 3
        if max_output_versions_int < 1:
            max_output_versions_int = 3
        self.max_output_versions = max_output_versions_int

        max_workers = enumerator.get("max_workers", "auto")
        self.max_workers = max_workers
        self.is_verbose = bool(enumerator.get("is_verbose", False))
        memory_budget = enumerator.get("memory_budget_mb", "auto")
        self.memory_budget_mb = memory_budget if memory_budget == "auto" else float(memory_budget)
        warmup = enumerator.get("warmup_batch_size", "auto")
        self.warmup_batch_size = warmup if warmup == "auto" else int(warmup)
        min_size = enumerator.get("min_batch_size", "auto")
        self.min_batch_size = min_size if min_size == "auto" else int(min_size)
        max_size = enumerator.get("max_batch_size", "auto")
        self.max_batch_size = max_size if max_size == "auto" else int(max_size)
        self.monitor_interval = int(enumerator.get("monitor_interval", 5))

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
        merged["enumerator"]["max_output_versions"] = self.max_output_versions
        merged["enumerator"]["max_workers"] = self.max_workers
        merged["enumerator"]["is_verbose"] = self.is_verbose
        merged["enumerator"]["memory_budget_mb"] = self.memory_budget_mb
        merged["enumerator"]["warmup_batch_size"] = self.warmup_batch_size
        merged["enumerator"]["min_batch_size"] = self.min_batch_size
        merged["enumerator"]["max_batch_size"] = self.max_batch_size
        merged["enumerator"]["monitor_interval"] = self.monitor_interval
        return merged
