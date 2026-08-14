"""Tag discovery 服务（磁盘扫描 + 验证 + 启用过滤）。

消费者: Tag facade / CLI / 后续 engines

本文件:
- DiscoveryService: 发现 tags 目录下全部/启用 tag
  边界: 负责文件夹扫描、key 唯一性、draft→DiscoveredTagInfo 升级；不负责 hooks 热路径或引擎执行
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from core.infra.project_context import ProjectContext

from core.modules.tag.core.services.discovery.data.discovered_tag import (
    DiscoveredTagInfo,
    TagDraft,
)

from .constants import TAG_FILE_NAME, TAG_SETTINGS_FILE_NAME
from .path_rules import TagPathRules

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Tag 发现服务。"""

    @staticmethod
    def discover_tags() -> List[DiscoveredTagInfo]:
        """发现全部 tag（UI 显示）。"""
        tags_root = ProjectContext.path.get_tags_root()

        if not tags_root.exists():
            logger.warning("Tag directory does not exist: %s", tags_root)
            return []

        drafts = DiscoveryService._scan_folders(tags_root)
        tags: List[DiscoveredTagInfo] = []
        keys_seen: Dict[str, str] = {}

        for draft in drafts:
            info = DiscoveredTagInfo.from_draft(draft)
            if info is None:
                continue

            if info.key in keys_seen:
                logger.error(
                    "Duplicate meta.key=%r: already used by %s",
                    info.key,
                    keys_seen[info.key],
                )
                continue
            keys_seen[info.key] = info.id()

            tags.append(info)

        return tags

    @staticmethod
    def get_enabled_tags(
        tags: Optional[List[DiscoveredTagInfo]] = None,
    ) -> List[DiscoveredTagInfo]:
        """筛选 ``is_enabled=True`` 的 tag。"""
        if tags is None:
            tags = DiscoveryService.discover_tags()
        return [info for info in tags if info.is_enabled]

    @staticmethod
    def find_tag(key_or_id: str) -> Optional[DiscoveredTagInfo]:
        """按 ``meta.key`` 或目录相对路径查找单个**已启用** tag。"""
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        for tag in DiscoveryService.get_enabled_tags():
            if tag.key == needle or tag.id() == needle:
                return tag
        return None

    @staticmethod
    def list_enabled_keys() -> List[str]:
        """已启用 tag 的 ``meta.key`` 列表（供 CLI 提示）。"""
        return [t.key for t in DiscoveryService.get_enabled_tags() if t.key]

    @staticmethod
    def _scan_folders(tags_root: Path) -> List[TagDraft]:
        """扫描 tag 文件夹，返回 TagDraft 列表。"""
        drafts: List[TagDraft] = []
        for dirpath, dirnames, _filenames in os.walk(tags_root):
            dirnames[:] = [d for d in dirnames if not str(d).startswith("_")]
            folder = Path(dirpath)
            tag_file = folder / TAG_FILE_NAME
            settings_file = folder / TAG_SETTINGS_FILE_NAME
            if tag_file.is_file() and settings_file.is_file():
                relative_path = TagPathRules.relative_tag_path(folder, tags_root)
                drafts.append(
                    TagDraft(
                        unique_relative_path=relative_path,
                        tag_file=tag_file,
                        settings_file=settings_file,
                    )
                )
        return drafts


__all__ = ["DiscoveryService"]
