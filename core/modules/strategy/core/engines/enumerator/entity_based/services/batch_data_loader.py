#!/usr/bin/env python3
"""批量数据加载服务（用于子进程 on_single_job_start 钩子）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey
from core.modules.strategy.core.engines.shared.services.entity_loader.gloabal_entity_loader import (
    GlobalEntityCache,
)

logger = logging.getLogger(__name__)


class BatchDataLoader:
    """批量数据加载服务。

    职责：
    1. 批量加载所有 entity_ids 的 per_entity 数据（entity_shared）
    2. 从共享内存读取 global 数据
    3. 返回结构化数据（供 execute_fn 使用）
    """

    @staticmethod
    def load_bundle_data(payload: Dict[str, Any]) -> Dict[str, Any]:
        """批量加载 bundle job 的所有数据。

        Args:
            payload: bundle job payload（包含 entity_specified, entity_shared, global, shm_info）

        Returns:
            Dict[str, Any]: 包含 entity_data 和 global_data 的结构

        结构：
        {
            "entity_data": {
                "600000.SH": {
                    "stockline.daily": [...],
                    "corporate_finance": [...]
                },
                "600001.SH": {
                    "stockline.daily": [...],
                    "corporate_finance": [...]
                }
            },
            "global_data": {
                "gdp": [...],
                "trade_calendar": [...]
            }
        }
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
            return {"entity_data": {}, "global_data": {}}

        logger.info(
            f"BatchDataLoader.load_bundle_data() 开始："
            f"entity_count={len(entity_ids)}, "
            f"per_entity_keys={len(entity_shared)}, "
            f"global_keys={len(global_keys)}"
        )

        # 3. 批量加载 per_entity 数据
        entity_data = BatchDataLoader._load_per_entity_data(
            entity_ids, entity_shared
        )

        # 4. 从共享内存读取 global 数据
        global_data = BatchDataLoader._load_global_data_from_shm(
            shm_info, global_keys
        )

        logger.info(
            f"BatchDataLoader.load_bundle_data() 完成："
            f"entity_data_count={len(entity_data)}, "
            f"global_data_count={len(global_data)}"
        )

        return {
            "entity_data": entity_data,
            "global_data": global_data,
        }

    @staticmethod
    def _load_per_entity_data(
        entity_ids: List[str],
        entity_shared: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """批量加载所有 entity_ids 的 per_entity 数据。

        Args:
            entity_ids: Entity ID 列表
            entity_shared: Per_entity 数据声明（data_key -> params）

        Returns:
            Dict[entity_id, Dict[data_key, data]]: 每个 entity 的完整数据

        流程：
        对每个 data_key：
        1. 使用 DataContracts.issue(entity_ids=...) 批量加载
        2. 从 IssueResult.by_entity 获取每个 entity 的数据
        3. 按 entity_id 组织数据
        """
        entity_data: Dict[str, Dict[str, Any]] = {}

        dcm = DataContracts()

        for data_key_str, params_dict in entity_shared.items():
            logger.info(f"批量加载 per_entity 数据：data_key={data_key_str}")

            try:
                # 提取参数
                start = params_dict.get("start")
                end = params_dict.get("end")
                params = params_dict.get("params", {})

                # 批量 issue（所有 entity_ids）
                result = dcm.issue(
                    DataKey(data_key_str),
                    entity_ids=entity_ids,
                    start=start,
                    end=end,
                    **params,
                )

                # 从 by_entity 获取每个 entity 的数据
                if result.by_entity:
                    for entity_id in entity_ids:
                        if entity_id in result.by_entity:
                            contract = result.by_entity[entity_id]

                            # 初始化 entity_data[entity_id]
                            if entity_id not in entity_data:
                                entity_data[entity_id] = {}

                            # 存储数据
                            entity_data[entity_id][data_key_str] = list(
                                contract.data or []
                            )

                    logger.info(
                        f"per_entity 数据加载成功：data_key={data_key_str}, "
                        f"entity_count={len(result.by_entity)}"
                    )
                else:
                    logger.warning(
                        f"per_entity 数据加载失败：data_key={data_key_str}, "
                        f"by_entity 为空"
                    )

            except Exception as e:
                logger.error(
                    f"per_entity 数据加载异常：data_key={data_key_str}, error={e}",
                    exc_info=True,
                )
                # 失败时填充空数据
                for entity_id in entity_ids:
                    if entity_id not in entity_data:
                        entity_data[entity_id] = {}
                    entity_data[entity_id][data_key_str] = []

        return entity_data

    @staticmethod
    def _load_global_data_from_shm(
        shm_info: Dict[str, Any],
        global_keys: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从共享内存读取 global 数据。

        Args:
            shm_info: 共享内存信息（shm_name, shm_size）
            global_keys: Global 数据声明（data_key -> {}）

        Returns:
            Dict[data_key, data]: Global 数据字典

        流程：
        1. 使用 GlobalEntityCache.access_shared_memory() 读取共享内存
        2. 返回 global 数据
        """
        if not global_keys:
            logger.info("global_keys 为空，无需读取共享内存")
            return {}

        shm_name = shm_info.get("shm_name", "")
        shm_size = shm_info.get("shm_size", 0)

        if not shm_name or shm_size <= 0:
            logger.warning("共享内存信息无效，无法读取 global 数据")
            return {}

        try:
            # 从共享内存读取 global 数据
            global_data = GlobalEntityCache.access_shared_memory(
                shm_name, shm_size
            )

            logger.info(
                f"global 数据读取成功：shm_name={shm_name}, "
                f"data_keys={list(global_data.keys())}"
            )

            return global_data

        except Exception as e:
            logger.error(
                f"global 数据读取失败：shm_name={shm_name}, error={e}",
                exc_info=True,
            )
            return {}


__all__ = ["BatchDataLoader"]