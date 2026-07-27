"""Tag BE 性能 profile（读取同目录 ``dispatch.yaml``）。

消费者: TagEntityPipeline, TagSlicePipeline
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, Optional

import yaml


class TagWorkerProfile:
    """``dispatch.yaml`` → entity_based / slice_based performance dict。"""

    _PATH: ClassVar[Path] = Path(__file__).with_name("dispatch.yaml")
    _cache: ClassVar[Optional[Dict[str, Any]]] = None

    @classmethod
    def _load_root(cls) -> Dict[str, Any]:
        if cls._cache is not None:
            return cls._cache
        if not cls._PATH.is_file():
            raise FileNotFoundError(f"tag dispatch config not found: {cls._PATH}")
        with cls._PATH.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"tag dispatch config must be a mapping: {cls._PATH}")
        cls._cache = data
        return data

    @classmethod
    def _merge_section(cls, section: str) -> Dict[str, Any]:
        cfg = cls._load_root()
        merged: Dict[str, Any] = {}
        default_block = cfg.get("default")
        if isinstance(default_block, dict):
            merged.update(default_block)
        section_block = cfg.get(section)
        if isinstance(section_block, dict):
            merged.update(section_block)
        return merged

    @classmethod
    def entity_based(cls) -> Dict[str, Any]:
        """entity_based dispatch（性能基准，用户不可覆盖）。"""
        return dict(cls._merge_section("entity_based"))

    @classmethod
    def slice_based(cls) -> Dict[str, Any]:
        """slice_based dispatch（性能基准，用户不可覆盖）。"""
        return dict(cls._merge_section("slice_based"))


__all__ = ["TagWorkerProfile"]
