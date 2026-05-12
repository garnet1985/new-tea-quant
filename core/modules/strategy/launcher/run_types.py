#!/usr/bin/env python3
"""运行期请求指纹数据类型（无 StrategySettings 顶层依赖，供 enumerator data_classes 安全导入）。"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Dict, List


@dataclass(frozen=True)
class StrategyRunFingerprint:
    schema_version: int
    strategy_name: str
    start_date: str
    end_date: str
    stock_ids: List[str]
    settings_core: Dict[str, Any]
    worker_module_path: str
    worker_class_name: str
    worker_code_hash: str
    data_contract_mapping: str
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
        data_contract_mapping: str = "",
    ) -> "StrategyRunFingerprint":
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_resolver import (
            semantic_core,
        )

        settings_core = semantic_core(raw_settings)
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
            data_contract_mapping=data_contract_mapping,
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
            data_contract_mapping=data_contract_mapping,
            fingerprint_id=fingerprint_id,
        )

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "StrategyRunFingerprint":
        dcm = payload.get("data_contract_mapping")
        if dcm is None or dcm == "":
            dcm = payload.get("data_contract_signature", "")
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
            data_contract_mapping=str(dcm or ""),
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
            "data_contract_mapping": self.data_contract_mapping,
            "fingerprint_id": self.fingerprint_id,
        }

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
        data_contract_mapping: str,
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
            "data_contract_mapping": data_contract_mapping,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_scope_fingerprint_id(fp: "StrategyRunFingerprint") -> str:
        """不含日历窗的 scope 指纹（DB / 工作台侧按策略语义对齐结果）。"""
        payload = {
            "v": 3,
            "kind": "strategy_run_scope",
            "strategy_name": fp.strategy_name,
            "stock_ids": list(fp.stock_ids),
            "settings_core": fp.settings_core,
            "worker_module_path": fp.worker_module_path,
            "worker_class_name": fp.worker_class_name,
            "worker_code_hash": fp.worker_code_hash,
            "data_contract_mapping": fp.data_contract_mapping,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["StrategyRunFingerprint"]
