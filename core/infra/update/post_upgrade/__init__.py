"""升级收尾（post-upgrade）动作：注册表 + 执行器。

公开推荐：``Update.post_upgrade``；本子包保留 CLI ``-m`` 入口。
"""
from core.infra.update.contracts import PostUpgradeRunResult
from core.infra.update.post_upgrade.registry import (
    get_post_upgrade_action,
    list_registered_actions,
    register_post_upgrade_action,
)
from core.infra.update.post_upgrade.runner import run_post_upgrade_actions

__all__ = [
    "register_post_upgrade_action",
    "list_registered_actions",
    "get_post_upgrade_action",
    "PostUpgradeRunResult",
    "run_post_upgrade_actions",
]
