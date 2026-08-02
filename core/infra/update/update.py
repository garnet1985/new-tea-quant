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
        from core.infra.update.db.registry import register_data_script

        return register_data_script(action_id, description=description)

    @staticmethod
    def get(action_id: str) -> Optional["RegisteredMigrationScript"]:
        from core.infra.update.db.registry import get_data_script

        return get_data_script(action_id)

    @staticmethod
    def list() -> Dict[str, "RegisteredMigrationScript"]:
        from core.infra.update.db.registry import list_registered_scripts

        return list_registered_scripts()

    @staticmethod
    def run(
        db: "DatabaseManager",
        action_id: str,
        *,
        context: Optional[dict] = None,
    ) -> None:
        from core.infra.update.db.registry import run_data_script

        run_data_script(db, action_id, context=context)


class PostUpgradeNamespace:
    """升级收尾动作注册表与执行器。"""

    @staticmethod
    def register(action_id: str, *, description: str = ""):
        from core.infra.update.post_upgrade.registry import register_post_upgrade_action

        return register_post_upgrade_action(action_id, description=description)

    @staticmethod
    def get(action_id: str) -> Optional["RegisteredPostUpgradeAction"]:
        from core.infra.update.post_upgrade.registry import get_post_upgrade_action

        return get_post_upgrade_action(action_id)

    @staticmethod
    def list() -> List["RegisteredPostUpgradeAction"]:
        from core.infra.update.post_upgrade.registry import list_registered_actions

        return list_registered_actions()

    @staticmethod
    def run(
        repo_root: Path,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> "PostUpgradeRunResult":
        from core.infra.update.post_upgrade.runner import run_post_upgrade_actions

        return run_post_upgrade_actions(repo_root, context=context)


class Update:
    """升级扩展门面（Facade）：数据脚本与 post-upgrade 收尾。"""

    data_scripts = DataScriptsNamespace()
    post_upgrade = PostUpgradeNamespace()


__all__ = ["Update"]
