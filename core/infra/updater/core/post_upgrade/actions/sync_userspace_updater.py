"""将编排源码同步到 ``userspace/system/updater``（升级后反向写盘）。"""
from __future__ import annotations

from pathlib import Path

from core.infra.updater.core.orchestrator_sync import sync_orchestrator
from core.infra.updater.core.post_upgrade.registry import PostUpgradeRegistry


@PostUpgradeRegistry.register(
    "sync_userspace_updater",
    description="将 core/infra/updater/core/orchestrator 同步到 userspace/system/updater",
)
def sync_userspace_updater(repo_root: Path, context: dict) -> None:
    dest = repo_root.resolve() / "userspace" / "system" / "updater"
    sync_orchestrator(dest)
