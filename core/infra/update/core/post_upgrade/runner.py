"""
执行已注册的 post-upgrade 收尾动作。
公开入口：``Update.post_upgrade.run``。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.update.contracts import (
    PostUpgradeRunResult,
    RegisteredPostUpgradeAction,
)
from core.infra.update.core.post_upgrade.registry import PostUpgradeRegistry

logger = logging.getLogger(__name__)


class PostUpgradeRunner:
    """按注册顺序执行收尾动作。"""

    @staticmethod
    def _ensure_actions_loaded() -> None:
        """触发 ``actions`` 包 import，使装饰器完成注册。"""
        from core.infra.update.core.post_upgrade import actions  # noqa: F401

    @staticmethod
    def run(
        repo_root: Path,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> PostUpgradeRunResult:
        """
        按注册顺序执行收尾动作；**注册表为空时直接跳过**（不报错）。
        """
        PostUpgradeRunner._ensure_actions_loaded()
        entries: List[RegisteredPostUpgradeAction] = PostUpgradeRegistry.list()
        if not entries:
            return PostUpgradeRunResult(
                skipped=True,
                skipped_reason="no registered post-upgrade actions",
            )

        root = repo_root.resolve()
        ctx = context if context is not None else {}
        executed: List[str] = []

        for entry in entries:
            logger.info("post-upgrade action: %s", entry.action_id)
            entry.run(root, ctx)
            executed.append(entry.action_id)

        return PostUpgradeRunResult(
            skipped=False,
            action_ids=executed,
            executed_count=len(executed),
        )
