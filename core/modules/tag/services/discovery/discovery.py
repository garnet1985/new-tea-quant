#!/usr/bin/env python3
"""
MIGRATED → ``core.modules.tag.core.services.discovery.DiscoveryService``

旧 discovery（``tag_worker.py`` + ``normalize_tag_settings`` + ``DiscoveredTag`` dict）。
新约定与 strategy 对齐::

    from core.modules.tag.core.services.discovery import DiscoveryService
    tags = DiscoveryService.discover_tags()
    enabled = DiscoveryService.get_enabled_tags()
    one = DiscoveryService.find_tag("market_cap_tier")  # meta.key 或路径

AUDIT: 待 TagManager / CLI / catalog 切走后删除本包。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from core.infra.discovery import Discovery

from core.modules.tag.config import get_scenarios_root
from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.models.scenario_model import ScenarioModel
from core.modules.tag.settings.normalize import normalize_tag_settings

from .path_rules import is_machine_readable_tag_path, relative_tag_key
from .worker_loader import load_tag_worker_class

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredTag:
    """Discovery 输出。

    .. deprecated::
        使用 ``TagInfo`` / ``EnabledTagInfo`` 替代。
    """

    tag_key: str
    folder: Path
    settings: Dict[str, Any]
    worker_class: Type[BaseTagWorker]
    worker_module_path: str
    worker_class_name: str
    worker_file_path: Path

    @property
    def settings_name(self) -> str:
        return str(self.settings.get("name") or self.tag_key)

    @property
    def module_key(self) -> str:
        return TagDiscoveryHelper._read_meta_key(self.settings, fallback=self.tag_key)


class TagDiscoveryHelper:
    """.. deprecated:: 使用 ``DiscoveryService`` 替代。"""

    @staticmethod
    def discover_tags(tags_root: Path | None = None) -> Dict[str, DiscoveredTag]:
        root = Path(tags_root) if tags_root is not None else get_scenarios_root()
        if not root.exists():
            logger.warning("Tag scenarios 根目录不存在: %s", root)
            return {}

        discovered: Dict[str, DiscoveredTag] = {}
        keys_seen: Dict[str, str] = {}
        for folder in TagDiscoveryHelper._iter_tag_directories(root):
            item = TagDiscoveryHelper.load_tag(folder, tags_root=root)
            if item is None:
                continue
            meta_key = item.module_key
            if meta_key in keys_seen:
                logger.error(
                    "Duplicate meta.key=%r: already used by %s (skip %s)",
                    meta_key,
                    keys_seen[meta_key],
                    item.tag_key,
                )
                continue
            keys_seen[meta_key] = item.tag_key
            discovered[item.tag_key] = item
            logger.info("发现 Tag 场景: %s (key=%s)", item.tag_key, meta_key)
        return discovered

    @staticmethod
    def _iter_tag_directories(tags_root: Path) -> List[Path]:
        root = Path(tags_root)
        candidates: List[Path] = []
        for dirpath, dirnames, _filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not str(d).startswith("_")]
            folder = Path(dirpath)
            if (folder / "settings.py").is_file() and (folder / "tag_worker.py").is_file():
                candidates.append(folder)
        candidates.sort(key=lambda p: relative_tag_key(p, root))
        return candidates

    @staticmethod
    def load_tag(
        tag_folder: Path,
        *,
        tags_root: Path | None = None,
    ) -> Optional[DiscoveredTag]:
        folder = Path(tag_folder)
        root = Path(tags_root) if tags_root is not None else get_scenarios_root()

        try:
            tag_key = relative_tag_key(folder, root)
        except ValueError:
            logger.warning("Tag 目录不在 tags_root 下: %s", folder)
            return None

        if not is_machine_readable_tag_path(tag_key):
            logger.warning(
                "Tag 路径含非 machine-readable 段，已跳过: %s",
                tag_key,
            )
            return None

        settings_file = folder / "settings.py"
        try:
            settings_dict = Discovery.file.load_python_config(settings_file, var_name="settings")
            if settings_dict is None:
                logger.error("加载 Tag settings 失败: %s", tag_key)
                return None
        except Exception as exc:
            logger.error("加载 Tag settings 失败: %s, error=%s", tag_key, exc)
            return None

        if not isinstance(settings_dict, dict):
            logger.error("Tag %s 的 settings 不是 dict", tag_key)
            return None

        TagDiscoveryHelper._ensure_meta_key(settings_dict, default_key=tag_key)

        try:
            normalized = normalize_tag_settings(settings_dict, tag_key=tag_key)
        except ValueError as exc:
            logger.warning("Tag %s settings 规范化失败: %s", tag_key, exc)
            return None
        if not ScenarioModel.is_setting_valid(normalized):
            logger.warning("Tag %s settings 校验未通过，已跳过", tag_key)
            return None

        worker_loaded = load_tag_worker_class(folder, tag_key)
        if not worker_loaded:
            logger.warning("Tag %s 无法加载 tag_worker.py", tag_key)
            return None
        worker_module_path, worker_class_name, worker_file_path, worker_class = worker_loaded

        return DiscoveredTag(
            tag_key=tag_key,
            folder=folder.resolve(),
            settings=settings_dict,
            worker_class=worker_class,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_file_path=worker_file_path,
        )

    @staticmethod
    def resolve_tag_key(
        name_or_key: str,
        discovered: Dict[str, DiscoveredTag],
    ) -> Optional[str]:
        """按 tag_key 或 meta.key 解析（后者须唯一）。"""
        key = str(name_or_key or "").strip()
        if not key:
            return None
        if key in discovered:
            return key
        matches = [k for k, item in discovered.items() if item.module_key == key]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            logger.warning(
                "Tag meta.key=%r 对应多个路径: %s，请使用完整 tag_key",
                key,
                ", ".join(matches),
            )
        return None

    @staticmethod
    def _read_meta_key(settings: Dict[str, Any], *, fallback: str = "") -> str:
        meta = settings.get("meta")
        if not isinstance(meta, dict):
            return str(fallback or "").strip()
        return str(meta.get("key") or fallback or "").strip()

    @staticmethod
    def _ensure_meta_key(settings: Dict[str, Any], *, default_key: str) -> str:
        meta = settings.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            settings["meta"] = meta
        key = str(meta.get("key") or "").strip()
        if key:
            return key
        key = str(default_key or "").strip()
        if not key:
            raise ValueError("meta.key 不能为空")
        meta["key"] = key
        return key


__all__ = ["DiscoveredTag", "TagDiscoveryHelper"]
