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
    "version": "0.4.2",
    "release_date": "2026-06-21",
    "description": "版本发布",
    "python": {"minimum": [3, 9]},
                                "new_features": [
        "重大更新：回测器和标签计算器支持多股并行的切片式回测",
        "使用多进程分散计算和数据预读取的方式加快效率",
        "加入探针，对切片进行自动大小分配以提高运行效率",
        "新增加低价策略来演示幸存者偏差",
        "(破坏性改动)重构tag的设置格式，分组并移除了一些配置，让配置更简单和直观",
        "增加了新的空的策略和标签模版，可以直接拷贝和修改",
        "重写了 cli 和 devcli",
        "ui新增加“高级功能”, 包含特征标签，数据源（暂时不能更新），数据契约",
        "在设置中增加了data.json全局数据管理的设置，并在一些页面显示被截断的警告，策略扫描演示模式的截止时间变成读取data.json",
        "给设置里增加清除缓存的功能",
        "在策略调试的界面加入“上一步”的按钮",
        "重新写了项目readme，更新用例",
        "清理了core/global_enums文件夹，将枚举分散到各自的主模块里",
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
