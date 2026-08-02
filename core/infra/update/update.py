"""Update 门面 — data_scripts / post_upgrade 注册表与执行。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.infra.db.contracts import DatabaseManager
    from core.infra.update.contracts import (
        PostUpgradeRunResult,
        RegisteredMigrationScript,
        RegisteredPostUpgradeAction,
    )


class DataScriptsNamespace:
    """DB 迁移用单步数据脚本注册表。"""

    @staticmethod
    def register(action_id: str, *, description: str = ""):
        from core.infra.update.db.registry import DataScriptRegistry

        return DataScriptRegistry.register(action_id, description=description)

    @staticmethod
    def get(action_id: str) -> Optional["RegisteredMigrationScript"]:
        from core.infra.update.db.registry import DataScriptRegistry

        return DataScriptRegistry.get(action_id)

    @staticmethod
    def list() -> Dict[str, "RegisteredMigrationScript"]:
        from core.infra.update.db.registry import DataScriptRegistry

        return DataScriptRegistry.list()

    @staticmethod
    def run(
        db: "DatabaseManager",
        action_id: str,
        *,
        context: Optional[dict] = None,
    ) -> None:
        from core.infra.update.db.registry import DataScriptRegistry

        DataScriptRegistry.run(db, action_id, context=context)


class PostUpgradeNamespace:
    """升级收尾动作注册表与执行器。"""

    @staticmethod
    def register(action_id: str, *, description: str = ""):
        from core.infra.update.post_upgrade.registry import PostUpgradeRegistry

        return PostUpgradeRegistry.register(action_id, description=description)

    @staticmethod
    def get(action_id: str) -> Optional["RegisteredPostUpgradeAction"]:
        from core.infra.update.post_upgrade.registry import PostUpgradeRegistry

        return PostUpgradeRegistry.get(action_id)

    @staticmethod
    def list() -> List["RegisteredPostUpgradeAction"]:
        from core.infra.update.post_upgrade.registry import PostUpgradeRegistry

        return PostUpgradeRegistry.list()

    @staticmethod
    def run(
        repo_root: Path,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> "PostUpgradeRunResult":
        from core.infra.update.post_upgrade.runner import PostUpgradeRunner

        return PostUpgradeRunner.run(repo_root, context=context)


class Update:
    """升级扩展门面（Facade）：数据脚本与 post-upgrade 收尾。"""

    data_scripts = DataScriptsNamespace()
    post_upgrade = PostUpgradeNamespace()


__all__ = ["Update"]
