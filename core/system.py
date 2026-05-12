"""
Core 版本与运行环境元信息（单一事实来源，在代码中维护）。

供 setup、ProjectContextManager、以及需要展示版本的模块使用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


class SystemMeta:
    def __init__(self) -> None:
        self._version = "0.3.0"
        self._release_date = "2026-05-11"
        self._description = "版本发布"
        # 与 JSON/序列化习惯一致用 list；比较时再转成 tuple
        self.python = {"minimum": [3, 9]}
        self.new_features: List[str] = [
            "重大更新：UI 系统发布（BFF + FED），引入 Node.js 依赖",
            "加入 Launder.py：一键启动与安装引导",
            "完成策略工作台与策略扫描的 UI 能力",
            "对齐 UI 与命令行的 Report 输出与展示",
            "回测加入缓存：重复回测将直接返回 Report",
            "Strategy 模块重构：按 flow 组织，更直观可维护",
        ]

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
