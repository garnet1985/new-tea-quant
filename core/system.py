"""
Core 版本与运行环境元信息。

**单一事实来源**：与本文件同目录的 ``system.json``（便于脚本/Updater 直接读取比对，无需 import Python）。
``SystemMeta`` 在运行时从该 JSON 加载；若文件缺失或损坏则回退到内置默认值并 ``warnings.warn``。
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

_DATA_PATH = Path(__file__).resolve().with_name("system.json")

_FALLBACK: Dict[str, Any] = {
    "version": "0.3.0",
    "release_date": "2026-05-11",
    "description": "版本发布",
    "python": {"minimum": [3, 9]},
    "new_features": [
        "重大更新：UI 系统发布（BFF + FED），引入 Node.js 依赖",
        "加入 Launder.py：一键启动与安装引导",
        "完成策略工作台与策略扫描的 UI 能力",
        "对齐 UI 与命令行的 Report 输出与展示",
        "回测加入缓存：重复回测将直接返回 Report",
        "Strategy 模块重构：按 flow 组织，更直观可维护",
    ],
}


def _load_payload() -> Dict[str, Any]:
    if not _DATA_PATH.is_file():
        warnings.warn(f"缺少 {_DATA_PATH.name}，使用内置回退版本信息", UserWarning, stacklevel=2)
        return dict(_FALLBACK)
    try:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        warnings.warn(f"无法解析 {_DATA_PATH}: {exc}；使用内置回退", UserWarning, stacklevel=2)
        return dict(_FALLBACK)
    if not isinstance(raw, dict) or not isinstance(raw.get("version"), str):
        warnings.warn(f"{_DATA_PATH.name} 结构无效；使用内置回退", UserWarning, stacklevel=2)
        return dict(_FALLBACK)
    return raw


class SystemMeta:
    def __init__(self) -> None:
        data = _load_payload()
        self._version = str(data.get("version", _FALLBACK["version"]))
        self._release_date = str(data.get("release_date", _FALLBACK["release_date"]))
        self._description = str(data.get("description", _FALLBACK["description"]))

        py = data.get("python") if isinstance(data.get("python"), dict) else {}
        lo = py.get("minimum")
        if isinstance(lo, list) and len(lo) >= 2:
            self.python = {"minimum": [int(lo[0]), int(lo[1])]}
        else:
            self.python = dict(_FALLBACK["python"])

        nf = data.get("new_features")
        if isinstance(nf, list) and all(isinstance(x, str) for x in nf):
            self.new_features: List[str] = list(nf)
        else:
            self.new_features = list(_FALLBACK["new_features"])

        plan = data.get("update_plan") if isinstance(data.get("update_plan"), dict) else {}
        ms = plan.get("managed_scope")
        if not (isinstance(ms, list) and all(isinstance(x, str) for x in ms)):
            ms = data.get("managed_scope")
        if isinstance(ms, list) and all(isinstance(x, str) for x in ms):
            self.managed_scope: List[str] = list(ms)
        else:
            self.managed_scope = []

        ig = plan.get("update_ignored_paths")
        if not (isinstance(ig, list) and all(isinstance(x, str) for x in ig)):
            ig = data.get("update_ignored_paths")
        if isinstance(ig, list) and all(isinstance(x, str) for x in ig):
            self.update_ignored_paths: List[str] = list(ig)
        else:
            self.update_ignored_paths = []

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
            "update_plan": {
                "managed_scope": list(self.managed_scope),
                "update_ignored_paths": list(self.update_ignored_paths),
            },
        }


# 模块级单例（避免各处重复构造）
system_meta = SystemMeta()


def get_version() -> str:
    return system_meta.version


def python_minimum() -> Tuple[int, int]:
    lo = system_meta.python["minimum"]
    return int(lo[0]), int(lo[1])
