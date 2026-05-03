#!/usr/bin/env python3
"""
策略运行指纹（全局）：规范化后的 `settings_core` + 运行维度；构造工具与 runtime 封装。

枚举磁盘产物不按旧 enumerator plan 复用；工作台侧 DB 以 fingerprint 对齐缓存命中（TTL / 版本漂移由 BFF 校验）。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Dict, List, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)


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
    ) -> "StrategyRunFingerprint":
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
    def from_dict(cls, payload: Dict[str, Any]) -> "StrategyRunFingerprint":
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

    @staticmethod
    def extract_settings_core(raw_settings: Dict[str, Any]) -> Dict[str, Any]:
        return StrategySettings.build_settings_core_for_fingerprint(raw_settings)

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
    def compute_scope_fingerprint_id(fp: "StrategyRunFingerprint") -> str:
        """不含日历窗的 scope 指纹（DB / 工作台侧按策略语义对齐结果）。"""
        payload = {
            "v": 2,
            "kind": "strategy_run_scope",
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


class StrategyFingerprintManager:
    """规范化 settings 与构建运行指纹。"""

    @staticmethod
    def canonicalize_settings(raw_settings: Dict[str, Any]) -> Dict[str, Any]:
        validated = StrategySettings(raw_settings=dict(raw_settings or {}))
        report = validated.validate()
        if not report.is_usable():
            raise ValueError("settings validation failed")
        return validated.to_dict()

    @staticmethod
    def build_run_fingerprint(
        *,
        flow_impl: Any,
        strategy_name: str,
        strategy_info: Any,
        settings_payload: Dict[str, Any],
        stock_ids: List[str],
    ) -> StrategyRunFingerprint:
        worker_ref = flow_impl.resolve_worker_blueprint(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
        )
        return flow_impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=copy.deepcopy(settings_payload),
            stock_ids=stock_ids,
            worker_ref=worker_ref,
        )

    @staticmethod
    def build_scope_fingerprint_id(fp: StrategyRunFingerprint) -> str:
        return str(StrategyRunFingerprint.compute_scope_fingerprint_id(fp) or "")


class StrategyFingerprintRuntimeService:
    """与 runtime context 配合的指纹辅助。"""

    @staticmethod
    def build_ids_for_runtime_context(context: Any) -> Tuple[str, str]:
        fp = StrategyFingerprintManager.build_run_fingerprint(
            flow_impl=context.flow._impl,
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
            settings_payload=context.settings_view.to_dict(),
            stock_ids=context.stock_list,
        )
        return str(fp.fingerprint_id or ""), StrategyFingerprintManager.build_scope_fingerprint_id(
            fp
        )

    @staticmethod
    def build_ids_from_request_fingerprint(
        request_fingerprint: Any,
    ) -> Tuple[str, str]:
        if request_fingerprint is None:
            return "", ""
        fp_id = str(getattr(request_fingerprint, "fingerprint_id", "") or "")
        if not fp_id:
            return "", ""
        return fp_id, StrategyFingerprintManager.build_scope_fingerprint_id(request_fingerprint)

    @staticmethod
    def build_fingerprint_for_snapshot_candidate(
        *,
        flow_ref: Any,
        strategy_name: str,
        strategy_info: Any,
        canonical_settings_payload: Dict[str, Any],
        stock_ids: List[str],
    ) -> Any:
        return StrategyFingerprintManager.build_run_fingerprint(
            flow_impl=flow_ref._impl,
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            settings_payload=canonical_settings_payload,
            stock_ids=stock_ids,
        )


__all__ = [
    "StrategyFingerprintManager",
    "StrategyFingerprintRuntimeService",
    "StrategyRunFingerprint",
]
