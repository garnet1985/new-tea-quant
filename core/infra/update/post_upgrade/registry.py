"""
升级收尾「反向」动作注册表。

在 ``managed_scope`` 镜像与 DB 迁移 **之后** 执行，用于 updater 无法在主流程中处理的写盘操作
（例如同步 ``userspace/system/updater``）。实现脚本可放在本包 ``actions/`` 子模块并通过本注册表挂接。
公开入口：``Update.post_upgrade``。
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from core.infra.update.contracts import PostUpgradeFn, RegisteredPostUpgradeAction

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, RegisteredPostUpgradeAction] = {}
_ORDER: List[str] = []


class PostUpgradeRegistry:
    """升级收尾动作注册表（方法挂靠本类）。"""

    @staticmethod
    def register(
        action_id: str,
        *,
        description: str = "",
    ) -> Callable[[PostUpgradeFn], PostUpgradeFn]:
        """装饰器：注册一条收尾动作（``action_id`` 全局唯一，按注册顺序执行）。"""

        def decorator(fn: PostUpgradeFn) -> PostUpgradeFn:
            key = action_id.strip()
            if not key:
                raise ValueError("PostUpgradeRegistry.register: action_id 不能为空")
            _REGISTRY[key] = RegisteredPostUpgradeAction(
                action_id=key,
                description=description or (fn.__doc__ or "").strip(),
                run=fn,
            )
            if key not in _ORDER:
                _ORDER.append(key)
            return fn

        return decorator

    @staticmethod
    def list() -> List[RegisteredPostUpgradeAction]:
        return [_REGISTRY[k] for k in _ORDER if k in _REGISTRY]

    @staticmethod
    def get(action_id: str) -> Optional[RegisteredPostUpgradeAction]:
        return _REGISTRY.get(action_id.strip()) if action_id else None

    @staticmethod
    def clear() -> None:
        """仅测试使用。"""
        _REGISTRY.clear()
        _ORDER.clear()
