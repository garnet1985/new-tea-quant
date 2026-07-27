#!/usr/bin/env python3
"""
MIGRATED → ``core.modules.tag.core.services.discovery.DiscoveryService``

旧 freestanding path helpers。新代码请使用::

    from core.modules.tag.core.services.discovery import TagPathRules

AUDIT: 待旧 TagManager / CLI 切到新 DiscoveryService 后删除本文件。
"""

from __future__ import annotations

import re
from pathlib import Path

# 与 strategy 一致：路径段须 machine-readable
TAG_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


def relative_tag_key(tag_folder: Path, tags_root: Path) -> str:
    folder = Path(tag_folder).resolve()
    root = Path(tags_root).resolve()
    return folder.relative_to(root).as_posix()


def is_machine_readable_tag_path(relative_path: str) -> bool:
    text = str(relative_path or "").strip().strip("/")
    if not text:
        return False
    segments = [seg for seg in text.split("/") if seg]
    if not segments:
        return False
    return all(bool(TAG_PATH_SEGMENT_RE.match(seg)) for seg in segments)


def tag_module_id(tag_key: str, *, suffix: str) -> str:
    safe = filesystem_safe_tag_key(tag_key)
    return f"_ntq_tag_{suffix}_{safe}"


def filesystem_safe_tag_key(tag_key: str) -> str:
    """将 ``tag_key`` 转为可安全用于文件名 / ``mkdtemp`` prefix 的 token。"""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", str(tag_key or "unknown")).strip("_")
    return safe or "unknown"


__all__ = [
    "TAG_PATH_SEGMENT_RE",
    "filesystem_safe_tag_key",
    "is_machine_readable_tag_path",
    "relative_tag_key",
    "tag_module_id",
]
