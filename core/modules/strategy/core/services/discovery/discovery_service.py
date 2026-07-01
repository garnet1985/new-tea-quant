"""Strategy discovery 服务（扫描 + 验证）。"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext

from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
    StrategyDraft,
    StrategyInfo,
)

from .constants import STRATEGY_FILE_NAME, STRATEGY_SETTINGS_FILE_NAME
from .path_rules import StrategyPathRules

logger = logging.getLogger(__name__)

class DiscoveryService:
    """策略发现服务（内部使用）。"""

    @staticmethod
    def discover_strategies() -> List[StrategyInfo]:
        """发现全部策略（UI显示）。"""
        strategies_root = ProjectContext.path.get_strategies_root()

        if not strategies_root.exists():
            logger.warning("Strategy directory does not exist: %s", strategies_root)
            return []

        drafts = DiscoveryService._scan_folders(strategies_root)
        strategies: List[StrategyInfo] = []
        keys_seen: Dict[str, str] = {}

        for draft in drafts:
            info = StrategyInfo.from_draft(draft)
            if info is None:
                continue

            # 检查key重复（key必须全局唯一）
            if info.key in keys_seen:
                logger.error(
                    "Duplicate meta.key=%r: already used by %s",
                    info.key,
                    keys_seen[info.key],
                )
                continue
            keys_seen[info.key] = info.id()

            strategies.append(info)
            logger.info(
                "Discovered strategy: %s (key=%s, enabled=%s)",
                info.id(),
                info.key,
                info.is_enabled,
            )

        return strategies

    @staticmethod
    def get_enabled_strategies(
        strategies: Optional[List[StrategyInfo]] = None,
    ) -> List[EnabledStrategyInfo]:
        """从策略列表中筛选出启用的策略。"""
        if strategies is None:
            strategies = DiscoveryService.discover_strategies()

        enabled: List[EnabledStrategyInfo] = []
        for info in strategies:
            if info.is_enabled:
                try:
                    enabled_info = EnabledStrategyInfo(**info.__dict__)
                    enabled.append(enabled_info)
                except ValueError as exc:
                    logger.warning(
                        "Failed to create EnabledStrategyInfo: %s, error: %s",
                        info.unique_relative_path,
                        exc,
                    )
        return enabled

    @staticmethod
    def find_strategy(key_or_id: str) -> Optional[EnabledStrategyInfo]:
        """按key或id查找单个启用的策略。"""
        enabled_strategies = DiscoveryService.get_enabled_strategies()
        for strategy in enabled_strategies:
            # 可以按key或id查找
            if strategy.key == key_or_id or strategy.id() == key_or_id:
                return strategy
        return None

    @staticmethod
    def _scan_folders(strategies_root: Path) -> List[StrategyDraft]:
        """扫描策略文件夹，返回 StrategyDraft 列表。"""
        drafts: List[StrategyDraft] = []
        for dirpath, dirnames, _filenames in os.walk(strategies_root):
            dirnames[:] = [d for d in dirnames if not str(d).startswith("_")]
            folder = Path(dirpath)
            strategy_file = folder / STRATEGY_FILE_NAME
            settings_file = folder / STRATEGY_SETTINGS_FILE_NAME
            if strategy_file.is_file() and settings_file.is_file():
                relative_path = StrategyPathRules.relative_strategy_path(
                    folder, strategies_root
                )
                drafts.append(
                    StrategyDraft(
                        folder=folder,
                        relative_path=relative_path,
                        strategy_file=strategy_file,
                        settings_file=settings_file,
                    )
                )
        return drafts

__all__ = ["DiscoveryService"]
