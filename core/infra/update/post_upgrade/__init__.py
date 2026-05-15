"""升级收尾（post-upgrade）动作：注册表 + 执行器。"""
from core.infra.update.post_upgrade.registry import (
    register_post_upgrade_action,
    list_registered_actions,
    get_post_upgrade_action,
)
from core.infra.update.post_upgrade.runner import PostUpgradeRunResult, run_post_upgrade_actions

__all__ = [
    "register_post_upgrade_action",
    "list_registered_actions",
    "get_post_upgrade_action",
    "PostUpgradeRunResult",
    "run_post_upgrade_actions",
]
