"""Tag 路径与动态 module id 命名规则。

消费者: DiscoveryService, TagHooksLoader

本文件:
- TagPathRules: 相对路径、机器可读段校验、``_ntq_tag_*`` module 名
  边界: 负责纯路径/命名规则；不负责 discovery 扫描或文件存在性
"""

from __future__ import annotations

import re
from pathlib import Path


class TagPathRules:
    """Tag 目录路径命名与 module id 规则。"""

    # 路径段：字母开头，仅 ASCII 字母、数字、下划线（与 strategy 一致）
    PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")

    @classmethod
    def relative_tag_path(cls, tag_folder: Path, tags_root: Path) -> str:
        """tags_root 到 tag 目录的相对 POSIX 路径（系统 tag_key）。"""
        folder = Path(tag_folder).resolve()
        root = Path(tags_root).resolve()
        return folder.relative_to(root).as_posix()

    @classmethod
    def is_machine_readable_path(cls, relative_path: str) -> bool:
        """路径各段是否满足机器可读命名。"""
        text = str(relative_path or "").strip().strip("/")
        if not text:
            return False
        segments = [seg for seg in text.split("/") if seg]
        if not segments:
            return False
        return all(bool(cls.PATH_SEGMENT_RE.match(seg)) for seg in segments)

    @classmethod
    def filesystem_safe_key(cls, tag_key: str) -> str:
        """将 tag_key 转为可安全用于文件名 / module 名的 token。"""
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", str(tag_key or "unknown")).strip("_")
        return safe or "unknown"

    @classmethod
    def tag_module_id(cls, tag_key: str, *, suffix: str) -> str:
        """生成稳定的动态加载 module 名（/ → _）。"""
        safe = cls.filesystem_safe_key(tag_key)
        return f"_ntq_tag_{suffix}_{safe}"


__all__ = ["TagPathRules"]
