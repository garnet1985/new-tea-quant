#!/usr/bin/env python3
"""策略路径 ID 规则（系统生成 name = strategies 下相对路径）。"""

from __future__ import annotations

import re
from pathlib import Path

# 路径段：字母开头，仅 ASCII 字母、数字、下划线（Decision 002）
STRATEGY_PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


def relative_strategy_key(strategy_folder: Path, strategies_root: Path) -> str:
    """``strategies_root`` 到策略目录的 POSIX 相对路径。"""
    folder = Path(strategy_folder).resolve()
    root = Path(strategies_root).resolve()
    rel = folder.relative_to(root)
    return rel.as_posix()


def is_machine_readable_strategy_path(relative_path: str) -> bool:
    text = str(relative_path or "").strip().strip("/")
    if not text:
        return False
    segments = [seg for seg in text.split("/") if seg]
    if not segments:
        return False
    return all(bool(STRATEGY_PATH_SEGMENT_RE.match(seg)) for seg in segments)


def strategy_module_id(strategy_key: str, *, suffix: str) -> str:
    """文件加载用稳定模块名（``/`` → ``_``）。"""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", str(strategy_key or "unknown"))
    return f"_ntq_strategy_{suffix}_{safe}"


__all__ = [
    "STRATEGY_PATH_SEGMENT_RE",
    "is_machine_readable_strategy_path",
    "relative_strategy_key",
    "strategy_module_id",
]
