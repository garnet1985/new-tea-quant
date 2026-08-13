"""
升级数据脚本注册表。

脚本实现放在本包；``core.infra.db`` 迁移执行器按 ``action_id``（通常即 ``update_key``）查找并调用。
公开入口：``Updater.data_scripts``。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Dict, Optional

from core.infra.updater.contracts import MigrationScriptFn, RegisteredMigrationScript

if TYPE_CHECKING:
    from core.infra.db.contracts import DatabaseManager

logger = logging.getLogger(__name__)


class DataScriptRegistry:
    """数据迁移脚本注册表（方法挂靠本类）。"""

    _REGISTRY: Dict[str, RegisteredMigrationScript] = {}

    @staticmethod
    def register(
        action_id: str,
        *,
        description: str = "",
    ) -> Callable[[MigrationScriptFn], MigrationScriptFn]:
        """装饰器：将函数注册为 ``action_id`` 对应的数据迁移脚本。"""

        def decorator(fn: MigrationScriptFn) -> MigrationScriptFn:
            key = action_id.strip()
            if not key:
                raise ValueError("DataScriptRegistry.register: action_id 不能为空")
            DataScriptRegistry._REGISTRY[key] = RegisteredMigrationScript(
                action_id=key,
                description=description or fn.__doc__ or "",
                run=fn,
            )
            return fn

        return decorator

    @staticmethod
    def get(action_id: str) -> Optional[RegisteredMigrationScript]:
        return (
            DataScriptRegistry._REGISTRY.get(action_id.strip()) if action_id else None
        )

    @staticmethod
    def list() -> Dict[str, RegisteredMigrationScript]:
        return dict(DataScriptRegistry._REGISTRY)

    @staticmethod
    def clear() -> None:
        """仅测试使用。"""
        DataScriptRegistry._REGISTRY.clear()

    @staticmethod
    def run(
        db: "DatabaseManager",
        action_id: str,
        *,
        context: Optional[dict] = None,
    ) -> None:
        """执行已注册脚本；未注册时抛出 ``KeyError``。"""
        entry = DataScriptRegistry.get(action_id)
        if entry is None:
            raise KeyError(f"未注册的数据迁移脚本: {action_id!r}")
        logger.info("run data migration script: %s", action_id)
        ctx = context if context is not None else {}
        entry.run(db, ctx)
