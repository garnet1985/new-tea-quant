"""
升级收尾「反向」动作注册表。

在 ``managed_scope`` 镜像与 DB 迁移 **之后** 执行，用于 updater 无法在主流程中处理的写盘操作
（例如同步 ``userspace/updater``）。实现脚本可放在本包 ``actions/`` 子模块并通过本注册表挂接。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

PostUpgradeFn = Callable[[Path, dict], None]


@dataclass(frozen=True)
class RegisteredPostUpgradeAction:
    action_id: str
    description: str
    run: PostUpgradeFn


_REGISTRY: Dict[str, RegisteredPostUpgradeAction] = {}
_ORDER: List[str] = []


def register_post_upgrade_action(
    action_id: str,
    *,
    description: str = "",
) -> Callable[[PostUpgradeFn], PostUpgradeFn]:
    """装饰器：注册一条收尾动作（``action_id`` 全局唯一，按注册顺序执行）。"""

    def decorator(fn: PostUpgradeFn) -> PostUpgradeFn:
        key = action_id.strip()
        if not key:
            raise ValueError("register_post_upgrade_action: action_id 不能为空")
        _REGISTRY[key] = RegisteredPostUpgradeAction(
            action_id=key,
            description=description or (fn.__doc__ or "").strip(),
            run=fn,
        )
        if key not in _ORDER:
            _ORDER.append(key)
        return fn

    return decorator


def list_registered_actions() -> List[RegisteredPostUpgradeAction]:
    return [_REGISTRY[k] for k in _ORDER if k in _REGISTRY]


def get_post_upgrade_action(action_id: str) -> Optional[RegisteredPostUpgradeAction]:
    return _REGISTRY.get(action_id.strip()) if action_id else None


def clear_post_upgrade_registry() -> None:
    """仅测试使用。"""
    _REGISTRY.clear()
    _ORDER.clear()
