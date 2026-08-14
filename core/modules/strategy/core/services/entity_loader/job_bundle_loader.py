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
from typing import Any, Dict, List, Optional

from core.modules.data_contract import ContractIssuer
from core.modules.strategy.core.services.entity_loader.contract_indicators import (
    ContractIndicators,
)
from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)

logger = logging.getLogger(__name__)


class JobBundleLoader:
    """按 payload 装载 job 数据面（使用方职责，非 BacktestEngine）。

    边界:
    - 负责: issue per_entity Contract、读 shm global、应用 indicators
    - 不负责: 日历推进、策略 hooks、CSV、job 调度
    - 调用方:
      - entity_based: ``load``（全窗一次）
      - slice_based: ``load_globals`` + 每正式片 ``load_per_entity_window``
    """

    @classmethod
    def load(cls, payload: Dict[str, Any], *, perf: Any = None) -> Dict[str, Any]:
        """全窗装载（entity_based）。start/end 取自 ``entity_shared``。"""
        entity_ids = cls._entity_ids_from_payload(payload)
        if not entity_ids:
            logger.warning("entity_ids 为空，无法加载数据")
            return {"entity_contracts": {}, "global_data": {}}

        entity_shared = payload.get("entity_shared", {})
        global_keys = payload.get("global", {})
        shm_info = payload.get("shm_info", {})

        logger.info(
            "JobBundleLoader.load() 开始：entity_count=%d, per_entity_keys=%d, global_keys=%d",
            len(entity_ids),
            len(entity_shared),
            len(global_keys),
        )

        entity_contracts = cls._issue_per_entity(
            entity_ids, entity_shared, start=None, end=None, perf=perf
        )
        global_data = cls.load_globals(payload)

        logger.info(
            "JobBundleLoader.load() 完成：entity_contracts=%d, global_keys=%d",
            len(entity_contracts),
            len(global_data),
        )
        return {
            "entity_contracts": entity_contracts,
            "global_data": global_data,
        }

    @classmethod
    def load_globals(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """仅读 shm globals（slice task 开头；per-entity 另按片装）。"""
        global_keys = payload.get("global", {})
        shm_info = payload.get("shm_info", {})
        return cls._load_global_data_from_shm(shm_info, global_keys)

    @classmethod
    def load_per_entity_window(
        cls,
        payload: Dict[str, Any],
        *,
        start: str,
        end: str,
        perf: Any = None,
    ) -> Dict[str, Any]:
        """按窗装载 per-entity contracts（覆盖 ``entity_shared`` 的 start/end）。

        Returns:
            ``entity_contracts`` dict only（不含 globals）。
        """
        start_s = str(start or "").strip()
        end_s = str(end or "").strip()
        if not start_s or not end_s:
            raise ValueError(
                f"load_per_entity_window 需要非空 start/end，收到 start={start!r} end={end!r}"
            )
        if start_s > end_s:
            start_s, end_s = end_s, start_s

        entity_ids = cls._entity_ids_from_payload(payload)
        if not entity_ids:
            logger.warning("entity_ids 为空，跳过 per-entity 窗装载")
            return {}

        entity_shared = payload.get("entity_shared", {})
        logger.info(
            "JobBundleLoader.load_per_entity_window()："
            "entities=%d keys=%d window=%s..%s",
            len(entity_ids),
            len(entity_shared),
            start_s,
            end_s,
        )
        return cls._issue_per_entity(
            entity_ids,
            entity_shared,
            start=start_s,
            end=end_s,
            perf=perf,
        )

    @classmethod
    def _entity_ids_from_payload(cls, payload: Dict[str, Any]) -> List[str]:
        entity_specified = payload.get("entity_specified", [])
        ids = [item["id"] for item in entity_specified if "id" in item]
        if ids:
            return ids
        raw = payload.get("entity_ids")
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        return []

    @classmethod
    def _issue_per_entity(
        cls,
        entity_ids: List[str],
        entity_shared: Dict[str, Dict[str, Any]],
        *,
        start: Optional[str],
        end: Optional[str],
        perf: Any = None,
    ) -> Dict[str, Any]:
        if perf is not None:
            perf.begin("load_contract_issue")
        entity_contracts = cls._load_per_entity_contracts(
            entity_ids,
            entity_shared,
            start_override=start,
            end_override=end,
            perf=perf,
        )
        if perf is not None:
            perf.end("load_contract_issue", accumulate=True)

        if perf is not None:
            perf.begin("load_apply_indicators")
        ContractIndicators.apply(entity_contracts, entity_shared)
        if perf is not None:
            perf.end("load_apply_indicators", accumulate=True)
        return entity_contracts

    @classmethod
    def _load_per_entity_contracts(
        cls,
        entity_ids: List[str],
        entity_shared: Dict[str, Dict[str, Any]],
        *,
        start_override: Optional[str] = None,
        end_override: Optional[str] = None,
        perf: Any = None,
    ) -> Dict[str, Any]:
        entity_contracts: Dict[str, Any] = {}
        for data_key_str, params_dict in entity_shared.items():
            logger.info("批量加载 per_entity Contract：data_key=%s", data_key_str)
            try:
                load_t0 = time.perf_counter()
                start = (
                    start_override
                    if start_override is not None
                    else params_dict.get("start")
                )
                end = (
                    end_override if end_override is not None else params_dict.get("end")
                )
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
                    elapsed_sec = time.perf_counter() - load_t0
                    if perf is not None:
                        perf.record_storage_load(data_key_str, elapsed_sec)
                    logger.info(
                        "per_entity Contract加载成功：data_key=%s entities=%d "
                        "window=%s..%s elapsed=%.2fs",
                        data_key_str,
                        len(entity_ids),
                        start,
                        end,
                        elapsed_sec,
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

    @classmethod
    def _load_global_data_from_shm(
        cls,
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
