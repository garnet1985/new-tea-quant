#!/usr/bin/env python3
"""Enumerator fingerprint for reuse planning."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, List
import json


_NON_CORE_ENUMERATOR_KEYS = {
    "max_workers",
    "is_verbose",
    "memory_budget_mb",
    "warmup_batch_size",
    "min_batch_size",
    "max_batch_size",
    "monitor_interval",
    "max_test_versions",
    "max_output_versions",
}

_NON_CORE_ROOT_KEYS = {
    "description",
    "is_enabled",
}


@dataclass(frozen=True)
class EnumeratorFingerprint:
    schema_version: int
    strategy_name: str
    start_date: str
    end_date: str
    stock_ids: List[str]
    settings_core: Dict[str, Any]
    worker_module_path: str
    worker_class_name: str
    worker_code_hash: str
    data_contract_signature: str
    fingerprint_id: str

    @classmethod
    def from_request(
        cls,
        *,
        strategy_name: str,
        start_date: str,
        end_date: str,
        stock_ids: List[str],
        raw_settings: Dict[str, Any],
        worker_module_path: str = "",
        worker_class_name: str = "",
        worker_code_hash: str = "",
        data_contract_signature: str = "",
    ) -> "EnumeratorFingerprint":
        settings_core = cls.extract_settings_core(raw_settings)
        normalized_stocks = sorted({str(stock_id) for stock_id in stock_ids if stock_id})
        fingerprint_id = cls.compute_fingerprint_id(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            stock_ids=normalized_stocks,
            settings_core=settings_core,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_code_hash=worker_code_hash,
            data_contract_signature=data_contract_signature,
        )
        return cls(
            schema_version=1,
            strategy_name=strategy_name,
            start_date=str(start_date),
            end_date=str(end_date),
            stock_ids=normalized_stocks,
            settings_core=settings_core,
            worker_module_path=str(worker_module_path),
            worker_class_name=str(worker_class_name),
            worker_code_hash=str(worker_code_hash),
            data_contract_signature=str(data_contract_signature),
            fingerprint_id=fingerprint_id,
        )

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "EnumeratorFingerprint":
        return cls(
            schema_version=int(payload.get("schema_version", 1)),
            strategy_name=str(payload.get("strategy_name", "")),
            start_date=str(payload.get("start_date", "")),
            end_date=str(payload.get("end_date", "")),
            stock_ids=sorted({str(s) for s in (payload.get("stock_ids") or [])}),
            settings_core=dict(payload.get("settings_core") or {}),
            worker_module_path=str(payload.get("worker_module_path", "")),
            worker_class_name=str(payload.get("worker_class_name", "")),
            worker_code_hash=str(payload.get("worker_code_hash", "")),
            data_contract_signature=str(payload.get("data_contract_signature", "")),
            fingerprint_id=str(payload.get("fingerprint_id", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "stock_ids": self.stock_ids,
            "settings_core": self.settings_core,
            "worker_module_path": self.worker_module_path,
            "worker_class_name": self.worker_class_name,
            "worker_code_hash": self.worker_code_hash,
            "data_contract_signature": self.data_contract_signature,
            "fingerprint_id": self.fingerprint_id,
        }

    def is_contain(self, request: "EnumeratorFingerprint") -> bool:
        if self.strategy_name and request.strategy_name != self.strategy_name:
            return False
        if request.start_date < self.start_date or request.end_date > self.end_date:
            return False
        if request.settings_core != self.settings_core:
            return False
        if request.worker_module_path != self.worker_module_path:
            return False
        if request.worker_class_name != self.worker_class_name:
            return False
        if request.worker_code_hash != self.worker_code_hash:
            return False
        if request.data_contract_signature != self.data_contract_signature:
            return False
        return set(request.stock_ids).issubset(set(self.stock_ids))

    def diff_stock_ids(self, request: "EnumeratorFingerprint") -> List[str]:
        return sorted(set(request.stock_ids) - set(self.stock_ids))

    @staticmethod
    def extract_settings_core(raw_settings: Dict[str, Any]) -> Dict[str, Any]:
        source = raw_settings or {}
        normalized_source = dict(source)
        enumerator = dict(normalized_source.get("enumerator") or {})
        for key in _NON_CORE_ENUMERATOR_KEYS:
            enumerator.pop(key, None)
        normalized_source["enumerator"] = enumerator
        # sampling 仅在任一模拟模块实际启用采样时参与 hash。
        # 否则 sampling 的编辑不应影响枚举缓存命中。
        sampling_is_used = bool(enumerator.get("use_sampling", False))
        price_cfg = normalized_source.get("price_simulator")
        if isinstance(price_cfg, dict) and bool(price_cfg.get("use_sampling", False)):
            sampling_is_used = True
        capital_cfg = normalized_source.get("capital_simulator")
        if isinstance(capital_cfg, dict) and bool(capital_cfg.get("use_sampling", False)):
            sampling_is_used = True
        if not sampling_is_used:
            normalized_source.pop("sampling", None)
        for key in _NON_CORE_ROOT_KEYS:
            normalized_source.pop(key, None)
        # meta（名称/描述等）不影响枚举计算；参与指纹会导致「仅改文案 / 版本切换」也换指纹，临时层与磁盘复用失真。
        normalized_source.pop("meta", None)
        # Keep full strategy config (except explicitly non-core keys) to avoid
        # stale cache reuse when strategy-specific params are changed.
        return normalized_source

    @staticmethod
    def compute_fingerprint_id(
        *,
        strategy_name: str,
        start_date: str,
        end_date: str,
        stock_ids: List[str],
        settings_core: Dict[str, Any],
        worker_module_path: str,
        worker_class_name: str,
        worker_code_hash: str,
        data_contract_signature: str,
    ) -> str:
        payload = {
            "strategy_name": strategy_name,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "stock_ids": stock_ids,
            "settings_core": settings_core,
            "worker_module_path": str(worker_module_path),
            "worker_class_name": str(worker_class_name),
            "worker_code_hash": str(worker_code_hash),
            "data_contract_signature": str(data_contract_signature),
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_enumerator_scope_fingerprint_id(fp: "EnumeratorFingerprint") -> str:
        """
        机会枚举在业务上不按日历窗口区分结果，但完整 fingerprint_id 含 start/end，
        会导致「隔日 / 默认 end_date 漂移」时无法命中 DB 临时层。scope 指纹去掉日期，仅保留
        策略名、股票池、settings_core、worker、数据契约签名。
        """
        payload = {
            "v": 1,
            "kind": "enumerator_scope",
            "strategy_name": fp.strategy_name,
            "stock_ids": list(fp.stock_ids),
            "settings_core": fp.settings_core,
            "worker_module_path": fp.worker_module_path,
            "worker_class_name": fp.worker_class_name,
            "worker_code_hash": fp.worker_code_hash,
            "data_contract_signature": fp.data_contract_signature,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["EnumeratorFingerprint"]
