#!/usr/bin/env python3
"""
Strategy settings dict-view model.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.data_contract.contract_const import DataKey


class StrategySettingsView:
    def __init__(self, settings_dict: Dict[str, Any]):
        self._settings = settings_dict
        self.name = settings_dict.get("name", "unknown")
        self.description = settings_dict.get("description", "")
        self.is_enabled = settings_dict.get("is_enabled", False)
        self.core = settings_dict.get("core", {})
        self.data = settings_dict.get("data", {})
        self.sampling = settings_dict.get("sampling", {})
        self.price_simulator = settings_dict.get("price_simulator", {})
        self.goal = settings_dict.get("goal", {})
        self.performance = settings_dict.get("performance", {})

    @staticmethod
    def normalize_base_required_data(raw: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("data.base_required_data 必须为 dict")
        params = raw.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValueError("data.base_required_data.params 必须为 dict")

        raw_id = raw.get("data_id")
        if raw_id is None or (isinstance(raw_id, str) and not raw_id.strip()):
            data_id = DataKey.STOCK_KLINE.value
        else:
            data_id = str(raw_id).strip()
            if data_id != DataKey.STOCK_KLINE.value:
                raise ValueError(
                    f"data.base_required_data.data_id 只能为 {DataKey.STOCK_KLINE.value!r} 或省略；"
                    "周期与复权请用 params.term / params.adjust"
                )

        term = params.get("term")
        if term is None or (isinstance(term, str) and not term.strip()):
            raise ValueError(
                "data.base_required_data.params 必须提供非空的 term（如 daily / weekly / monthly）"
            )

        merged = dict(params)
        if "adjust" not in merged or (
            isinstance(merged.get("adjust"), str)
            and not str(merged.get("adjust")).strip()
        ):
            merged["adjust"] = "qfq"

        return {"data_id": data_id, "params": merged}

    @staticmethod
    def normalize_extra_required_data_item(item: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError("数据源项必须为 dict")
        raw_id = item.get("data_id")
        if not raw_id or not str(raw_id).strip():
            raise ValueError("extra_required_data_sources 每项必须包含非空的 data_id")
        data_id = str(raw_id).strip()

        params = item.get("params")
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            raise ValueError("数据源 params 必须为 dict")

        if data_id == DataKey.STOCK_KLINE.value:
            term = params.get("term")
            if term is None or (isinstance(term, str) and not term.strip()):
                raise ValueError(
                    f"data_id 为 {DataKey.STOCK_KLINE.value} 时 params 必须提供非空的 term"
                )
            merged = dict(params)
            if "adjust" not in merged or (
                isinstance(merged.get("adjust"), str)
                and not str(merged.get("adjust")).strip()
            ):
                merged["adjust"] = "qfq"
            return {"data_id": data_id, "params": merged}

        return {"data_id": data_id, "params": dict(params)}

    @staticmethod
    def validate_data_config(data: Dict[str, Any]) -> None:
        base = data.get("base_required_data")
        if not isinstance(base, dict):
            raise ValueError("data.base_required_data 必须为 dict")
        StrategySettingsView.normalize_base_required_data(base)

        extra = data.get("extra_required_data_sources", [])
        if extra is None:
            return
        if not isinstance(extra, list):
            raise ValueError("data.extra_required_data_sources 必须为 list")
        for i, item in enumerate(extra):
            if not isinstance(item, dict):
                raise ValueError(f"data.extra_required_data_sources[{i}] 必须为 dict")
            try:
                StrategySettingsView.normalize_extra_required_data_item(item)
            except ValueError as e:
                raise ValueError(f"data.extra_required_data_sources[{i}]: {e}") from e

    @property
    def base_required_data(self) -> Dict[str, Any]:
        b = self.data.get("base_required_data")
        if not isinstance(b, dict):
            raise ValueError("缺少 data.base_required_data")
        return b

    @property
    def extra_required_data_sources(self) -> List[Dict[str, Any]]:
        xs = self.data.get("extra_required_data_sources", [])
        if xs is None or not isinstance(xs, list):
            return []
        return list(xs)

    @property
    def required_data_sources(self) -> List[Dict[str, Any]]:
        base = self.normalize_base_required_data(self.base_required_data)
        rest = [
            self.normalize_extra_required_data_item(x)
            for x in self.extra_required_data_sources
        ]
        return [base] + rest

    @property
    def resolved_base_required_data(self) -> Dict[str, Any]:
        return self.normalize_base_required_data(self.base_required_data)

    @property
    def min_required_records(self) -> int:
        return int(self.data.get("min_required_records", 100) or 100)

    @property
    def adjust_type(self) -> str:
        p = self.resolved_base_required_data.get("params") or {}
        return str(p.get("adjust", "qfq"))

    @property
    def indicators(self) -> Dict[str, Any]:
        return self.data.get("indicators", {}) or {}

    @property
    def tag_storage_entity_type(self) -> str:
        p = self.resolved_base_required_data.get("params") or {}
        return str(p.get("tag_storage_entity_type", "stock_kline_daily"))

    @property
    def start_date(self) -> str:
        s = self.sampling if isinstance(self.sampling, dict) else {}
        return str(s.get("start_date", "") or "").strip()

    @property
    def end_date(self) -> str:
        s = self.sampling if isinstance(self.sampling, dict) else {}
        return str(s.get("end_date", "") or "").strip()

    @property
    def sampling_amount(self) -> int:
        return int(self.sampling.get("sampling_amount", 10) or 10)

    @property
    def sampling_config(self) -> Dict[str, Any]:
        return self.sampling

    @property
    def max_workers(self) -> Any:
        simulator_cfg = self.price_simulator or {}
        enumerator_cfg = self.get("enumerator") or {}
        performance_cfg = self.performance or {}
        return (
            simulator_cfg.get("max_workers")
            or enumerator_cfg.get("max_workers")
            or performance_cfg.get("max_workers")
            or "auto"
        )

    def to_dict(self) -> Dict[str, Any]:
        return self._settings

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategySettingsView":
        return cls(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)


__all__ = ["StrategySettingsView"]
