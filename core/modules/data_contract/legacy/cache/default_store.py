"""进程内默认 ContractCacheManager（Facade 黑盒 cache 用）。"""
from __future__ import annotations

from core.modules.data_contract.core.cache.contract_cache_manager import ContractCacheManager

_default_cache: ContractCacheManager | None = None


def shared_contract_cache() -> ContractCacheManager:
    global _default_cache
    if _default_cache is None:
        _default_cache = ContractCacheManager()
    return _default_cache


def reset_shared_contract_cache() -> None:
    """单测隔离用。"""
    global _default_cache
    if _default_cache is not None:
        _default_cache.clear_all()
    _default_cache = None
