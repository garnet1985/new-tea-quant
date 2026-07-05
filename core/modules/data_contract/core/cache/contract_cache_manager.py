"""ContractCacheManager - 统一的 Contract 缓存管理器。"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.data_contract.core.data_class.base_contract import BaseDataKey

logger = logging.getLogger(__name__)


class ContractCacheManager:
    """Contract 缓存管理器（统一的 store + fingerprint 管理）。

    设计理念：
    - Contract.data：存储数据（自身 cache）
    - Contract.fingerprint：管理 fingerprint，判断是否需要刷新
    - Manager：提供统一的 store（记录已缓存的 fingerprint）
    - 生命周期管理：业务层逻辑，不在 Contract 职责内

    职责：
    1. 提供统一的 store（可选分开成 global/per-strategy store）
    2. 管理 fingerprint（记录已缓存的 fingerprint）
    3. 判断是否需要刷新缓存（fingerprint 是否变化）
    4. 清理缓存（按 fingerprint 或全部清理）

    使用方式：
        cache_mgr = ContractCacheManager()

        # Contract 管理 fingerprint
        contract = pool.get_contract("macro.gdp")
        contract.fill_in_data(runtime={...})
        # contract.data 存储数据，contract.fingerprint 记录 fingerprint

        # Manager 判断是否需要刷新
        if cache_mgr.needs_refresh(contract):
            contract.fill_in_data(runtime={...}, force_reload=True)

        # Manager 清理缓存
        cache_mgr.clear_cache(contract.fingerprint)
    """

    def __init__(self):
        """初始化 ContractCacheManager。"""
        # 统一的 store：记录已缓存的 fingerprint
        # fingerprint -> Contract.data（不存储数据副本，只记录 fingerprint）
        self._cached_fingerprints: Dict[str, bool] = {}  # fingerprint -> is_cached

    def calculate_fingerprint(self, contract: 'BaseDataKey') -> str:
        """计算 Contract fingerprint（由整个 runtime 决定）。

        Args:
            contract: Contract 实例

        Returns:
            str: SHA256 fingerprint

        设计理念：
        - Fingerprint 由 runtime 决定（包含所有 runtime 字段）
        - 不包含 specific（specific 是静态声明，不影响缓存）
        - 不包含 data_key（data_key 已在 runtime 中体现）
        """
        # 提取 runtime 的所有字段
        runtime_data = {}
        for key, value in vars(contract.runtime).items():
            # 过滤掉内部字段（如 __dict__, __weakref__ 等）
            if not key.startswith('_'):
                runtime_data[key] = value

        # 序列化并计算 SHA256
        fingerprint_str = json.dumps(runtime_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

    def needs_refresh(self, contract: 'BaseDataKey') -> bool:
        """判断是否需要刷新缓存（fingerprint 是否变化）。

        Args:
            contract: Contract 实例

        Returns:
            bool: True 如果需要刷新，False 如果不需要

        逻辑：
        - 如果 contract 未加载（is_loaded=False），需要加载
        - 如果 fingerprint 未缓存，需要加载
        - 如果 contract.fingerprint 与当前不同，需要刷新
        """
        # 如果 contract 未加载，需要加载
        if not contract.is_loaded:
            return True

        # 计算 fingerprint
        fingerprint = self.calculate_fingerprint(contract)

        # 如果 fingerprint 未缓存，需要加载
        if fingerprint not in self._cached_fingerprints:
            return True

        # 如果 contract 的 fingerprint 与当前不同，需要刷新
        if contract.fingerprint != fingerprint:
            return True

        return False

    def mark_cached(self, contract: 'BaseDataKey') -> None:
        """标记 Contract 已缓存（记录 fingerprint）。

        Args:
            contract: Contract 实例
        """
        fingerprint = self.calculate_fingerprint(contract)
        self._cached_fingerprints[fingerprint] = True
        contract.fingerprint = fingerprint
        logger.debug(f"标记已缓存: {contract.meta.data_key} -> {fingerprint}")

    def clear_cache(self, fingerprint: str) -> None:
        """清理指定 fingerprint 的缓存。

        Args:
            fingerprint: 缓存 fingerprint
        """
        if fingerprint in self._cached_fingerprints:
            del self._cached_fingerprints[fingerprint]
            logger.debug(f"清理缓存: {fingerprint}")

    def clear_all(self) -> None:
        """清理所有缓存。"""
        self._cached_fingerprints.clear()
        logger.info("清理所有缓存")

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息。

        Returns:
            Dict[str, int]: 缓存统计
        """
        return {
            "cached_count": len(self._cached_fingerprints),
        }

    def is_cached(self, fingerprint: str) -> bool:
        """检查 fingerprint 是否已缓存。

        Args:
            fingerprint: 缓存 fingerprint

        Returns:
            bool: 是否已缓存
        """
        return fingerprint in self._cached_fingerprints


__all__ = ['ContractCacheManager']