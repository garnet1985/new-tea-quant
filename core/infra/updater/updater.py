"""Updater 门面 — data_scripts / post_upgrade / runtime.sync_orchestrator。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .contracts import (
    MigrationScriptFn,
    PostUpgradeFn,
    PostUpgradeRunResult,
    RegisteredMigrationScript,
    RegisteredPostUpgradeAction,
)

if TYPE_CHECKING:
    from core.infra.db.contracts import DatabaseManager


class TypesNamespace:
    """与 ``contracts`` 同源的类型挂载点。"""

    MigrationScriptFn = MigrationScriptFn
    PostUpgradeFn = PostUpgradeFn
    RegisteredMigrationScript = RegisteredMigrationScript
    RegisteredPostUpgradeAction = RegisteredPostUpgradeAction
    PostUpgradeRunResult = PostUpgradeRunResult


class DataScriptsNamespace:
    """DB 迁移用单步数据脚本注册表。"""

    @staticmethod
    def register(action_id: str, *, description: str = ""):
        from core.infra.updater.core.db.registry import DataScriptRegistry

        return DataScriptRegistry.register(action_id, description=description)

    @staticmethod
    def get(action_id: str) -> Optional[RegisteredMigrationScript]:
        from core.infra.updater.core.db.registry import DataScriptRegistry

        return DataScriptRegistry.get(action_id)

    @staticmethod
    def list() -> Dict[str, RegisteredMigrationScript]:
        from core.infra.updater.core.db.registry import DataScriptRegistry

        return DataScriptRegistry.list()

    @staticmethod
    def run(
        db: "DatabaseManager",
        action_id: str,
        *,
        context: Optional[dict] = None,
    ) -> None:
        from core.infra.updater.core.db.registry import DataScriptRegistry

        DataScriptRegistry.run(db, action_id, context=context)


class PostUpgradeNamespace:
    """升级收尾动作注册表与执行器。"""

    @staticmethod
    def register(action_id: str, *, description: str = ""):
        from core.infra.updater.core.post_upgrade.registry import PostUpgradeRegistry

        return PostUpgradeRegistry.register(action_id, description=description)

    @staticmethod
    def get(action_id: str) -> Optional[RegisteredPostUpgradeAction]:
        from core.infra.updater.core.post_upgrade.registry import PostUpgradeRegistry

        return PostUpgradeRegistry.get(action_id)

    @staticmethod
    def list() -> List[RegisteredPostUpgradeAction]:
        from core.infra.updater.core.post_upgrade.registry import PostUpgradeRegistry

        return PostUpgradeRegistry.list()

    @staticmethod
    def run(
        repo_root: Path,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> PostUpgradeRunResult:
        from core.infra.updater.core.post_upgrade.runner import PostUpgradeRunner

        return PostUpgradeRunner.run(repo_root, context=context)


class RuntimeNamespace:
    """运行时拷贝（userspace updater）；不在此启动升级流水线。"""

    @staticmethod
    def sync_orchestrator(dest: Path) -> List[str]:
        from core.infra.updater.core.orchestrator_sync import sync_orchestrator

        return sync_orchestrator(dest)


class Updater:
    """升级门面：扩展点 + 将编排源码同步到 userspace。"""

    data_scripts = DataScriptsNamespace()
    post_upgrade = PostUpgradeNamespace()
    runtime = RuntimeNamespace
    types = TypesNamespace


__all__ = ["Updater"]
