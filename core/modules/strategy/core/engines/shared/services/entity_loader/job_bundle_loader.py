"""Job bundle 数据面加载（per-entity contracts + shm globals）。

消费者: scanner, enumerator
（整块消费者见 entity_loader/__init__.py）

本文件:
- JobBundleLoader: issue per_entity Contract、读 shm、应用 indicators
  边界: 负责 worker task 数据装载；不负责日历推进、hooks 或 CSV 落盘
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from core.modules.data_contract import ContractIssuer
from core.modules.strategy.core.engines.shared.services.entity_loader.contract_indicators import (
    ContractIndicators,
)
from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)

logger = logging.getLogger(__name__)


class JobBundleLoader:
    """按 payload 装载 job 数据面（使用方职责，非 BacktestEngine）。

    边界:
    - 负责: issue per_entity Contract、读 shm global、应用 indicators
    - 不负责: 日历推进、策略 hooks、CSV、job 调度
    - 调用方: enumerator JobExecutor.on_before_task_start（写入 job_context.init）
    """

    @staticmethod
    def load(payload: Dict[str, Any], *, perf: Any = None) -> Dict[str, Any]:
        entity_specified = payload.get("entity_specified", [])
        entity_shared = payload.get("entity_shared", {})
        global_keys = payload.get("global", {})
        shm_info = payload.get("shm_info", {})

        entity_ids = [item["id"] for item in entity_specified if "id" in item]
        if not entity_ids:
            logger.warning("entity_ids 为空，无法加载数据")
            return {"entity_contracts": {}, "global_data": {}}

        logger.info(
            "JobBundleLoader.load() 开始：entity_count=%d, per_entity_keys=%d, global_keys=%d",
            len(entity_ids),
            len(entity_shared),
            len(global_keys),
        )

        if perf is not None:
            perf.begin("load_contract_issue")
        entity_contracts = JobBundleLoader._load_per_entity_contracts(
            entity_ids, entity_shared, perf=perf
        )
        if perf is not None:
            perf.end("load_contract_issue", accumulate=True)

        if perf is not None:
            perf.begin("load_apply_indicators")
        ContractIndicators.apply(entity_contracts, entity_shared)
        if perf is not None:
            perf.end("load_apply_indicators", accumulate=True)

        global_data = JobBundleLoader._load_global_data_from_shm(shm_info, global_keys)

        logger.info(
            "JobBundleLoader.load() 完成：entity_contracts=%d, global_keys=%d",
            len(entity_contracts),
            len(global_data),
        )
        return {
            "entity_contracts": entity_contracts,
            "global_data": global_data,
        }

    @staticmethod
    def _load_per_entity_contracts(
        entity_ids: List[str],
        entity_shared: Dict[str, Dict[str, Any]],
        *,
        perf: Any = None,
    ) -> Dict[str, Any]:
        entity_contracts: Dict[str, Any] = {}
        for data_key_str, params_dict in entity_shared.items():
            logger.info("批量加载 per_entity Contract：data_key=%s", data_key_str)
            try:
                load_t0 = time.perf_counter()
                start = params_dict.get("start")
                end = params_dict.get("end")
                params = params_dict.get("params", {})
                runtime = {"entity_ids": entity_ids, **params}
                if start:
                    runtime["start"] = start
                if end:
                    runtime["end"] = end

                contract = ContractIssuer.issue(
                    data_key_str,
                    entity_ids=entity_ids,
                    runtime=runtime,
                    fill_in_data=True,
                )
                if contract.is_loaded and contract.data:
                    entity_contracts[data_key_str] = contract
                    if perf is not None:
                        perf.record_storage_load(
                            data_key_str,
                            time.perf_counter() - load_t0,
                        )
                    logger.info(
                        "per_entity Contract加载成功：data_key=%s",
                        data_key_str,
                    )
                else:
                    logger.warning(
                        "per_entity Contract加载失败：data_key=%s",
                        data_key_str,
                    )
            except Exception as exc:
                logger.error(
                    "per_entity Contract加载异常：data_key=%s error=%s",
                    data_key_str,
                    exc,
                    exc_info=True,
                )
        return entity_contracts

    @staticmethod
    def _load_global_data_from_shm(
        shm_info: Dict[str, Any],
        global_keys: Dict[str, Any],
    ) -> Dict[str, Any]:
        _ = global_keys
        info = shm_info if isinstance(shm_info, dict) else {}
        shm_name = str(info.get("shm_name") or "").strip()
        try:
            shm_size = int(info.get("shm_size") or 0)
        except (TypeError, ValueError):
            shm_size = 0
        if not shm_name or shm_size <= 0:
            # 空 shm 是合法路径（scanner / 未挂 GlobalEntityCache）；仅残缺配置才告警
            if shm_name or info.get("shm_size") not in (None, "", 0, "0"):
                logger.warning("共享内存信息无效，无法读取 global 数据")
            else:
                logger.debug("无 shm_info，跳过 global 数据读取")
            return {}
        try:
            global_data = GlobalEntityCache.access_shared_memory(shm_name, shm_size)
            logger.info(
                "global 数据读取成功：shm_name=%s keys=%s",
                shm_name,
                list(global_data.keys()),
            )
            return global_data
        except Exception as exc:
            logger.error(
                "global 数据读取失败：shm_name=%s error=%s",
                shm_name,
                exc,
                exc_info=True,
            )
            return {}


__all__ = ["JobBundleLoader"]
