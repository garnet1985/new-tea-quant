"""跨模块契约：数据迁移脚本与 post-upgrade 动作类型。

推荐::

    from core.infra.update import Update
    from core.infra.update.contracts import (
        PostUpgradeRunResult,
        RegisteredMigrationScript,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from core.infra.db.contracts import DatabaseManager

MigrationScriptFn = Callable[["DatabaseManager", dict], None]
PostUpgradeFn = Callable[[Path, dict], None]


@dataclass(frozen=True)
class RegisteredMigrationScript:
    action_id: str
    description: str
    run: MigrationScriptFn


@dataclass(frozen=True)
class RegisteredPostUpgradeAction:
    action_id: str
    description: str
    run: PostUpgradeFn


@dataclass
class PostUpgradeRunResult:
    skipped: bool = False
    skipped_reason: Optional[str] = None
    action_ids: List[str] = field(default_factory=list)
    executed_count: int = 0


__all__ = [
    "MigrationScriptFn",
    "PostUpgradeFn",
    "RegisteredMigrationScript",
    "RegisteredPostUpgradeAction",
    "PostUpgradeRunResult",
]
