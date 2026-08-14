"""收尾动作实现；``load_builtins`` 保证测试 clear 之后仍能装回内置动作。"""
from __future__ import annotations

from core.infra.updater.core.post_upgrade.registry import PostUpgradeRegistry


def load_builtins() -> None:
    from core.infra.updater.core.post_upgrade.actions import (
        sync_userspace_updater as _sync_mod,
    )

    if PostUpgradeRegistry.get("sync_userspace_updater") is None:
        PostUpgradeRegistry.register(
            "sync_userspace_updater",
            description="将 core/infra/updater/core/orchestrator 同步到 userspace/system/updater",
        )(_sync_mod.sync_userspace_updater)
