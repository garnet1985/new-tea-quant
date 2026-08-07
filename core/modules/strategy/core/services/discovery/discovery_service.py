"""Strategy discovery 服务（磁盘扫描 + 验证 + 启用过滤）。

本文件:
- DiscoveryService: 发现 strategies 目录下全部/启用策略
  边界: 负责文件夹扫描、key 唯一性、draft→StrategyInfo 升级；不负责 hooks 热路径调用或回测
"""
from __future__ import annotations

from dataclasses import fields
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
            # logger.info(
            #     "Discovered strategy: %s (key=%s, enabled=%s)",
            #     info.id(),
            #     info.key,
            #     info.is_enabled,
            # )

        return strategies

    @staticmethod
    def get_enabled_strategies(
        strategies: Optional[List[StrategyInfo]] = None,
    ) -> List[EnabledStrategyInfo]:
        """从策略列表中筛选出启用的策略。"""
        if strategies is None:
            strategies = DiscoveryService.discover_strategies()

        enabled: List[EnabledStrategyInfo] = []
        field_names = {f.name for f in fields(EnabledStrategyInfo) if f.init}
        for info in strategies:
            if info.is_enabled:
                try:
                    kwargs = {k: v for k, v in info.__dict__.items() if k in field_names}
                    enabled_info = EnabledStrategyInfo(**kwargs)
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
        """按 ``meta.key``（CLI alias）或目录相对路径查找单个启用的策略。"""
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        enabled_strategies = DiscoveryService.get_enabled_strategies()
        for strategy in enabled_strategies:
            if strategy.key == needle or strategy.id() == needle:
                return strategy
        return None

    @staticmethod
    def resolve_strategy_path(key_or_name: str) -> str:
        """``meta.key`` 或 path name → userspace 相对 path（含未启用策略）。

        Raises:
            ValueError: 空 needle
            FileNotFoundError: 发现列表中无匹配
        """
        needle = str(key_or_name or "").strip()
        if not needle:
            raise ValueError("strategy_key_or_name 不能为空")
        for info in DiscoveryService.discover_strategies():
            if info.key == needle or info.id() == needle:
                return str(info.id())
        raise FileNotFoundError(f"策略不存在: {needle!r}")

    @staticmethod
    def resolve_strategy_folder(key_or_name: str) -> Path:
        """``meta.key`` / relative path → discovered absolute strategy folder.

        Falls back to ``userspace/strategies/{name}`` when not in the catalog
        (bootstrap / legacy callers).
        """
        from core.infra.project_context import ProjectContext

        needle = str(key_or_name or "").strip()
        if not needle:
            raise ValueError("strategy_key_or_name 不能为空")
        for info in DiscoveryService.discover_strategies():
            if info.key == needle or info.id() == needle:
                return info.resolved_folder()
        enabled = DiscoveryService.find_strategy(needle)
        if enabled is not None:
            return enabled.resolved_folder()
        return ProjectContext.path.coerce_strategy_folder(needle)

    @staticmethod
    def list_enabled_keys() -> List[str]:
        """已启用策略的 ``meta.key`` 列表（供 CLI 提示）。"""
        return [s.key for s in DiscoveryService.get_enabled_strategies() if s.key]

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
                        unique_relative_path=relative_path,
                        strategy_file=strategy_file,
                        settings_file=settings_file,
                    )
                )
        return drafts

__all__ = ["DiscoveryService"]
