"""
Core 版本与运行环境元信息（单一事实来源，在代码中维护）。

供 setup、ProjectContextManager、以及需要展示版本的模块使用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


class SystemMeta:
    def __init__(self) -> None:
        self._version = "0.2.1"
        self._release_date = "2026-04-14"
        self._description = "版本发布"
        # 与 JSON/序列化习惯一致用 list；比较时再转成 tuple
        self.python = {"minimum": [3, 9]}
        self.new_features: List[str] = []

    @property
    def version(self) -> str:
        return self._version

    @property
    def release_date(self) -> str:
        return self._release_date

    @property
    def description(self) -> str:
        return self._description

    def is_python_compatible(self, python_version: Tuple[int, int]) -> bool:
        lo = self.python["minimum"]
        return python_version >= (int(lo[0]), int(lo[1]))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self._version,
            "release_date": self._release_date,
            "description": self._description,
            "python": {"minimum": list(self.python["minimum"])},
            "new_features": list(self.new_features),
        }


# 模块级单例（避免各处重复构造）
system_meta = SystemMeta()


def get_version() -> str:
    return system_meta.version


def python_minimum() -> Tuple[int, int]:
    lo = system_meta.python["minimum"]
    return int(lo[0]), int(lo[1])
