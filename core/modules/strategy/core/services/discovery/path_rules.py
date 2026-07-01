"""Strategy 路径 ID 规则。"""
from __future__ import annotations

import re
from pathlib import Path


class StrategyPathRules:
    """策略目录路径命名与 module id 规则。"""

    # 路径段：字母开头，仅 ASCII 字母、数字、下划线（Decision 002）
    PATH_SEGMENT_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")

    @classmethod
    def relative_strategy_key(cls, strategy_folder: Path, strategies_root: Path) -> str:
        """strategies_root 到策略目录的相对 POSIX 路径。"""
        folder = Path(strategy_folder).resolve()
        root = Path(strategies_root).resolve()
        rel = folder.relative_to(root)
        return rel.as_posix()

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

    @staticmethod
    def strategy_module_id(strategy_key: str, *, suffix: str) -> str:
        """生成稳定的动态加载 module 名（/ → _）。"""
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", str(strategy_key or "unknown"))
        return f"_ntq_strategy_{suffix}_{safe}"


__all__ = ["StrategyPathRules"]
