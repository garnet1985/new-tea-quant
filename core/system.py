"""
Core 版本与运行环境元信息。

**单一事实来源**：与本文件同目录的 ``system.json``。
``SystemMeta`` 在运行时从该 JSON 加载；文件缺失、损坏或必填字段无效时直接报错（无静默回退）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

_DATA_PATH = Path(__file__).resolve().with_name("system.json")


def _require_str(data: Dict[str, Any], key: str) -> str:
    raw = data.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{_DATA_PATH.name} 缺少有效字符串字段 {key!r}")
    return raw.strip()


def _require_str_list(data: Dict[str, Any], key: str) -> List[str]:
    raw = data.get(key)
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise ValueError(f"{_DATA_PATH.name} 字段 {key!r} 须为字符串数组")
    return list(raw)


def _require_python_minimum(data: Dict[str, Any]) -> Dict[str, List[int]]:
    py = data.get("python")
    if not isinstance(py, dict):
        raise ValueError(f"{_DATA_PATH.name} 缺少 object 字段 python")
    lo = py.get("minimum")
    if not (isinstance(lo, list) and len(lo) >= 2):
        raise ValueError(f"{_DATA_PATH.name} python.minimum 须为 [major, minor]")
    try:
        major, minor = int(lo[0]), int(lo[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{_DATA_PATH.name} python.minimum 须为整数对") from exc
    return {"minimum": [major, minor]}


def _require_update_plan(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    plan = data.get("update_plan")
    if not isinstance(plan, dict):
        raise ValueError(f"{_DATA_PATH.name} 缺少 object 字段 update_plan")
    managed = plan.get("managed_scope")
    ignored = plan.get("update_ignored_paths")
    if not (isinstance(managed, list) and all(isinstance(x, str) for x in managed)):
        raise ValueError(f"{_DATA_PATH.name} update_plan.managed_scope 须为字符串数组")
    if not (isinstance(ignored, list) and all(isinstance(x, str) for x in ignored)):
        raise ValueError(
            f"{_DATA_PATH.name} update_plan.update_ignored_paths 须为字符串数组"
        )
    return list(managed), list(ignored)


def _load_payload() -> Dict[str, Any]:
    if not _DATA_PATH.is_file():
        raise FileNotFoundError(f"缺少核心元数据文件: {_DATA_PATH}")
    try:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法解析 {_DATA_PATH}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{_DATA_PATH.name} 根须为 JSON object")
    return raw


class SystemMeta:
    def __init__(self) -> None:
        data = _load_payload()
        self._version = _require_str(data, "version")
        self._release_date = _require_str(data, "release_date")
        self._description = _require_str(data, "description")
        self.python = _require_python_minimum(data)
        self.new_features = _require_str_list(data, "new_features")
        self.managed_scope, self.update_ignored_paths = _require_update_plan(data)

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
