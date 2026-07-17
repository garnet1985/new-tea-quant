#!/usr/bin/env python3
"""批量数据加载服务（用于子进程 on_child_process_task_start 钩子）。"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from core.modules.data_contract import ContractIssuer
from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)

logger = logging.getLogger(__name__)


class BatchDataLoader:
    """批量数据加载（entity / slice 子进程共用）。

    边界:
    - 负责: 批量 issue per_entity Contract、读 shm global、应用 indicators
    - 不负责: 枚举模拟、CSV 落盘
    - 调用方: entity_based / slice_based JobExecutor.on_child_process_task_start
    """

    @staticmethod
    def load_bundle_data(
        payload: Dict[str, Any],
        *,
        perf: Any = None,
    ) -> Dict[str, Any]:
        """批量加载 bundle job 的所有数据（返回Contract实例）。

        Args:
            payload: bundle job payload（包含 entity_specified, entity_shared, global, shm_info）

        Returns:
            Dict[str, Any]: 包含 entity_contracts（Contract实例）和 global_data 的结构

        结构：
        {
            "entity_contracts": {
                "stock.kline.daily": Contract实例（包含所有entity_ids的数据）,
                "stock.finance.quarterly": Contract实例,
            },
            "global_data": {
                "gdp": [...],
                "trade_calendar": [...]
            }
        }

        设计：
        - 返回Contract实例，支持until(as_of)方法（PIT推进）
        - Contract内部维护每个entity的独立cursor状态
        - 避免重复创建Contract实例（一个data_key一个Contract，包含所有entity_ids）
        """
        # 1. 解析 payload
        entity_specified = payload.get("entity_specified", [])
        entity_shared = payload.get("entity_shared", {})
        global_keys = payload.get("global", {})
        shm_info = payload.get("shm_info", {})

        # 2. 获取所有 entity_ids
        entity_ids = [item["id"] for item in entity_specified if "id" in item]

        if not entity_ids:
            logger.warning("entity_ids 为空，无法加载数据")
            return {"entity_contracts": {}, "global_data": {}}

        logger.info(
            f"BatchDataLoader.load_bundle_data() 开始："
            f"entity_count={len(entity_ids)}, "
            f"per_entity_keys={len(entity_shared)}, "
            f"global_keys={len(global_keys)}"
        )

        # 3. 批量加载 per_entity 数据（返回Contract实例）
        if perf is not None:
            perf.begin("load_contract_issue")
        entity_contracts = BatchDataLoader._load_per_entity_contracts(
            entity_ids, entity_shared, perf=perf
        )
        if perf is not None:
            perf.end("load_contract_issue", accumulate=True)

        from core.modules.strategy.core.engines.enumerator.shared.services.contract_indicators import (
            ContractIndicators,
        )

        if perf is not None:
            perf.begin("load_apply_indicators")
        ContractIndicators.apply(entity_contracts, entity_shared)
        if perf is not None:
            perf.end("load_apply_indicators", accumulate=True)

        # 4. 从共享内存读取 global 数据
        global_data = BatchDataLoader._load_global_data_from_shm(
            shm_info, global_keys
        )

        logger.info(
            f"BatchDataLoader.load_bundle_data() 完成："
            f"entity_contracts_count={len(entity_contracts)}, "
            f"global_data_count={len(global_data)}"
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
        """批量加载所有 entity_ids 的 per_entity Contract实例。

        Args:
            entity_ids: Entity ID 列表
            entity_shared: Per_entity 数据声明（data_key -> params）

        Returns:
            Dict[data_key, Contract实例]: 每个data_key的Contract实例（包含所有entity_ids的数据）

        流程：
        对每个 data_key：
        1. 使用 ContractIssuer.issue() 批量加载
        2. 返回Contract实例（支持until方法）
        3. Contract内部维护每个entity的独立cursor状态

        设计：
        - 一个data_key一个Contract实例（包含所有entity_ids的数据）
        - Contract.data格式：{entity_id: data_rows}
        - Contract内部有cursor_states：{entity_id: CursorState}
        - 避免为每个entity创建Contract实例（节省内存）
        """
        entity_contracts: Dict[str, Any] = {}

        for data_key_str, params_dict in entity_shared.items():
            logger.info(f"批量加载 per_entity Contract：data_key={data_key_str}")

            try:
                load_t0 = time.perf_counter()
                # 提取参数
                start = params_dict.get("start")
                end = params_dict.get("end")
                params = params_dict.get("params", {})

                # 构建runtime参数（包含entity_ids和params）
                runtime = {
                    "entity_ids": entity_ids,
                    **params,
                }

                # 如果有start/end，添加到runtime
                if start:
                    runtime["start"] = start
                if end:
                    runtime["end"] = end

                # 使用 ContractIssuer.issue() 批量加载（返回Contract实例）
                contract = ContractIssuer.issue(
                    data_key_str,
                    entity_ids=entity_ids,  # 批量传递所有entity_ids
                    runtime=runtime,
                    fill_in_data=True,  # 自动加载数据
                )

                # 检查Contract是否加载成功
                if contract.is_loaded and contract.data:
                    # 存储Contract实例
                    entity_contracts[data_key_str] = contract
                    if perf is not None:
                        perf.record_storage_load(
                            data_key_str,
                            time.perf_counter() - load_t0,
                        )

                    logger.info(
                        f"per_entity Contract加载成功：data_key={data_key_str}, "
                        f"entity_count={len(contract.data) if isinstance(contract.data, dict) else 'N/A'}"
                    )
                else:
                    logger.warning(
                        f"per_entity Contract加载失败：data_key={data_key_str}, "
                        f"Contract未加载或data为空"
                    )

            except Exception as e:
                logger.error(
                    f"per_entity Contract加载异常：data_key={data_key_str}, error={e}",
                    exc_info=True,
                )
                # 失败时跳过该data_key
                continue

        return entity_contracts

    @staticmethod
    def _load_global_data_from_shm(
        shm_info: Dict[str, Any],
        global_keys: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从共享内存读取 global 数据（含系统 global：stock.list、trade.calendar）。"""
        _ = global_keys  # 策略声明 keys；系统 global 已在 shm 中，一并返回

        shm_name = shm_info.get("shm_name", "")
        shm_size = shm_info.get("shm_size", 0)

        if not shm_name or shm_size <= 0:
            logger.warning("共享内存信息无效，无法读取 global 数据")
            return {}

        try:
            global_data = GlobalEntityCache.access_shared_memory(shm_name, shm_size)
            logger.info(
                "global 数据读取成功：shm_name=%s, data_keys=%s",
                shm_name,
                list(global_data.keys()),
            )
            return global_data
        except Exception as exc:
            logger.error(
                "global 数据读取失败：shm_name=%s, error=%s",
                shm_name,
                exc,
                exc_info=True,
            )
            return {}


__all__ = ["BatchDataLoader"]