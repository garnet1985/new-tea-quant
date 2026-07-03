"""entity_based child process（子进程执行逻辑）。"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ChildProcessWorker:
    """entity_based child process（子进程执行）。

    钩子方法：
    - on_init: 子进程开始前（数据加载）
    - execute: 子进程执行（调用hooks.find_opportunity）
    - on_release: 子进程结束后（资源清理）
    """

    @staticmethod
    def on_init(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """子进程开始前钩子：批量数据加载。

        Args:
            job_id: bundle job id（如 "strategy_run"）
            payload: bundle job payload（包含 entity_specified, entity_shared, global, shm_info）

        Returns:
            Dict[str, Any]: 包含 entity_data 和 global_data 的结构

        流程：
        1. 使用 BatchDataLoader 批量加载所有 entity_ids 的数据
        2. 返回结构化数据（供 execute 使用）
        """
        logger.info("Child process init: job_id=%s", job_id)

        from core.modules.strategy.core.engines.enumerator.entity_based.services.batch_data_loader import (
            BatchDataLoader,
        )

        # 批量加载 bundle 数据
        loaded_data = BatchDataLoader.load_bundle_data(payload)

        logger.info(
            "Child process init 完成：entity_count=%d, global_keys=%d",
            len(loaded_data.get("entity_data", {})),
            len(loaded_data.get("global_data", {})),
        )

        return loaded_data

    @staticmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """子进程执行函数：调用hooks.find_opportunity()。

        Args:
            payload: job payload

        Returns:
            执行结果（包含opportunities等）
        """
        entity_id = payload.get("entity_id")
        logger.info("Child process execute: entity_id=%s", entity_id)

        # TODO: 实现执行逻辑
        # 1. 从payload提取hooks_class、settings、data等
        # 2. 加载entity contracts
        # 3. 调用hooks.find_opportunity()
        # 4. 返回opportunities

        # 暂时返回空结果
        return {
            "success": True,
            "entity_id": entity_id,
            "opportunities": [],
        }

    @staticmethod
    def on_release(job_id: str, payload: Dict[str, Any]) -> None:
        """子进程结束后钩子：资源清理。

        Args:
            job_id: entity_id
            payload: job payload
        """
        logger.info("Child process release: entity_id=%s", job_id)

        # TODO: 实现资源清理逻辑
        # - 清理entity数据
        # - 释放内存


__all__ = ["ChildProcess"]