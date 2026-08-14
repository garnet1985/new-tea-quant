"""对已加载 per-entity Contract 批量应用声明 indicators。

消费者: scanner, enumerator（经 JobBundleLoader）
（整块消费者见 entity_loader/__init__.py）

本文件:
- ContractIndicators: Indicator.compute_batch 写回 kline rows
  边界: 负责 indicator 注入；不负责 Contract issue 或 job 编排
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.indicator import Indicator

logger = logging.getLogger(__name__)


class ContractIndicators:
    """对已 load 的 per-entity Contract 批量写入声明的 indicators。

    边界:
    - 负责: 按 entity_shared.indicators 计算并写回 kline rows
    - 不负责: Contract 加载 / job 编排
    - 调用方: JobBundleLoader
    """

    @staticmethod
    def _field_name(name: str, params: Dict[str, Any]) -> str:
        name = name.lower()
        length = params.get("length")
        if length is not None and isinstance(length, (int, float, str)):
            return f"{name}{int(length)}"
        parts = [name]
        for key in sorted(params.keys()):
            value = params[key]
            if isinstance(value, (int, float, str)):
                parts.append(f"{key}{value}")
        return "_".join(parts)

    @staticmethod
    def _apply_to_rows(
        rows: List[Dict[str, Any]],
        indicators_cfg: Dict[str, Any],
    ) -> None:
        for name, cfg, result in Indicator.compute_batch(rows, indicators_cfg):
            try:
                if isinstance(result, list):
                    field = ContractIndicators._field_name(name, cfg)
                    for rec, val in zip(rows, result):
                        rec[field] = val
                elif isinstance(result, dict):
                    for key, series in result.items():
                        field = ContractIndicators._field_name(f"{name}_{key}", cfg)
                        for rec, val in zip(rows, series):
                            rec[field] = val
            except Exception as exc:
                logger.error(
                    "写入指标失败: indicator=%s params=%s error=%s",
                    name,
                    cfg,
                    exc,
                )

    @staticmethod
    def apply(
        entity_contracts: Dict[str, Any],
        entity_shared: Dict[str, Dict[str, Any]],
    ) -> None:
        for data_key, params_dict in entity_shared.items():
            indicators_cfg = params_dict.get("indicators") or {}
            if not indicators_cfg:
                continue
            contract = entity_contracts.get(data_key)
            if contract is None or not getattr(contract, "is_loaded", False):
                continue
            data = getattr(contract, "data", None)
            if not isinstance(data, dict):
                continue
            for _entity_id, rows in data.items():
                if not isinstance(rows, list) or not rows:
                    continue
                ContractIndicators._apply_to_rows(rows, indicators_cfg)


__all__ = ["ContractIndicators"]
