"""
升级数据脚本注册表。

脚本实现放在本包；``core.infra.db`` 迁移执行器按 ``action_id``（通常即 ``update_key``）查找并调用。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, Optional

if TYPE_CHECKING:
    from core.infra.db.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

MigrationScriptFn = Callable[["DatabaseManager", dict], None]


@dataclass(frozen=True)
class RegisteredMigrationScript:
    action_id: str
    description: str
    run: MigrationScriptFn


_REGISTRY: Dict[str, RegisteredMigrationScript] = {}


def register_data_script(
    action_id: str,
    *,
    description: str = "",
) -> Callable[[MigrationScriptFn], MigrationScriptFn]:
    """装饰器：将函数注册为 ``action_id`` 对应的数据迁移脚本。"""

    def decorator(fn: MigrationScriptFn) -> MigrationScriptFn:
        key = action_id.strip()
        if not key:
            raise ValueError("register_data_script: action_id 不能为空")
        _REGISTRY[key] = RegisteredMigrationScript(
            action_id=key,
            description=description or fn.__doc__ or "",
            run=fn,
        )
        return fn

    return decorator


def get_data_script(action_id: str) -> Optional[RegisteredMigrationScript]:
    return _REGISTRY.get(action_id.strip()) if action_id else None


def list_registered_scripts() -> Dict[str, RegisteredMigrationScript]:
    return dict(_REGISTRY)


def run_data_script(
    db: "DatabaseManager",
    action_id: str,
    *,
    context: Optional[dict] = None,
) -> None:
    """执行已注册脚本；未注册时抛出 ``KeyError``。"""
    entry = get_data_script(action_id)
    if entry is None:
        raise KeyError(f"未注册的数据迁移脚本: {action_id!r}")
    logger.info("run data migration script: %s", action_id)
    ctx = context if context is not None else {}
    entry.run(db, ctx)
