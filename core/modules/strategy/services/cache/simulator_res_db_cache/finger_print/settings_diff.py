#!/usr/bin/env python3
"""
**Settings差异计算和筛选服务**。

核心设计：
- 缓存只存储"影响回测结果的差异字段"
- 指纹基于差异字段（diff和filter之后的output）
- merge：物理settings（基准） + 缓存的差异字段 = 用户修改过的settings

流程：
拿到物理settings -> 和用户修改过的settings比较diff -> 得到了不同的字段 -> 筛选出这些字段中会影响回测结果的字段 -> 将这些筛选过后的字段入库
"""

from __future__ import annotations

import copy
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# 影响回测结果的字段（指纹字段）
# 这些字段的变化会导致回测结果不同，需要参与指纹计算
# 注意：enumerator 字段是运行参数，不影响回测结果，所以不参与指纹计算
FINGERPRINT_FIELDS: FrozenSet[str] = frozenset(
    {
        "core",
        "data",
        "goal",
        "sampling",
        "price_simulator",
        "capital_simulator",
        "fees",
        "simulation",
        "market_profile",
    }
)

# 不影响回测结果的字段（展示字段）
# 这些字段的变化不会导致回测结果不同，不参与指纹计算
NON_FINGERPRINT_FIELDS: FrozenSet[str] = frozenset(
    {
        "meta",
        "is_enabled",
        "scanner",
    }
)


def _is_fingerprint_field(field_path: str) -> bool:
    """判断字段路径是否影响回测结果。

    Args:
        field_path: 字段路径（例如 "core.threshold"）

    Returns:
        是否影响回测结果
    """
    # 根级字段判断
    root_field = field_path.split(".")[0]
    return root_field in FINGERPRINT_FIELDS


def _deep_diff(
    dict_a: Dict[str, Any],
    dict_b: Dict[str, Any],
    path: str = "",
) -> Dict[str, Any]:
    """深度对比两个字典的差异。

    Args:
        dict_a: 字典A（基准）
        dict_b: 字典B（对比）
        path: 当前路径（用于递归）

    Returns:
        差异字典（只包含dict_b相对于dict_a的差异）
    """
    diff: Dict[str, Any] = {}

    for key in dict_b:
        current_path = f"{path}.{key}" if path else key
        value_a = dict_a.get(key)
        value_b = dict_b[key]

        # dict_b有但dict_a没有的（新增）
        if key not in dict_a:
            diff[key] = copy.deepcopy(value_b)
            continue

        # 值不同
        if isinstance(value_a, dict) and isinstance(value_b, dict):
            # 递归对比嵌套字典
            nested_diff = _deep_diff(value_a, value_b, current_path)
            if nested_diff:
                diff[key] = nested_diff
        elif value_a != value_b:
            # 值不同（非嵌套）
            diff[key] = copy.deepcopy(value_b)

    return diff


def diff_settings(
    disk_settings: Dict[str, Any],
    user_modified_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """对比磁盘上的 settings 和用户修改过的 settings 的差异。

    Args:
        disk_settings: 磁盘上的 settings（基准）
        user_modified_settings: 用户修改过的 settings（对比）

    Returns:
        差异字典（只包含用户修改过的 settings 相对于磁盘上的 settings 的差异）
    """
    return _deep_diff(disk_settings, user_modified_settings)


def filter_fingerprint_fields(
    diff: Dict[str, Any],
) -> Dict[str, Any]:
    """筛选影响回测结果的差异字段。

    Args:
        diff: 差异字典

    Returns:
        筛选后的差异字典（只包含影响回测结果的字段）
    """
    filtered: Dict[str, Any] = {}

    for key in diff:
        if _is_fingerprint_field(key):
            filtered[key] = copy.deepcopy(diff[key])

    return filtered


def diff_and_filter(
    disk_settings: Dict[str, Any],
    user_modified_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """计算差异并筛选影响回测结果的字段。

    Args:
        disk_settings: 磁盘上的 settings（基准）
        user_modified_settings: 用户修改过的 settings（对比）

    Returns:
        筛选后的差异字典（只包含影响回测结果的字段）
    """
    diff = diff_settings(disk_settings, user_modified_settings)
    filtered = filter_fingerprint_fields(diff)
    return filtered


def _deep_merge(
    base: Dict[str, Any],
    diff: Dict[str, Any],
) -> Dict[str, Any]:
    """深度合并基准字典和差异字典。

    Args:
        base: 基准字典（磁盘上的 settings）
        diff: 差异字典（缓存）

    Returns:
        合并后的字典（用户修改过的 settings）
    """
    merged = copy.deepcopy(base)

    for key in diff:
        value_diff = diff[key]
        value_base = merged.get(key)

        if isinstance(value_base, dict) and isinstance(value_diff, dict):
            # 递归合并嵌套字典
            merged[key] = _deep_merge(value_base, value_diff)
        else:
            # 直接覆盖（新增或修改）
            merged[key] = copy.deepcopy(value_diff)

    return merged


def merge_settings(
    disk_settings: Dict[str, Any],
    cached_diff: Dict[str, Any],
) -> Dict[str, Any]:
    """合并磁盘上的 settings 和缓存的差异字段。

    Args:
        disk_settings: 磁盘上的 settings（基准）
        cached_diff: 缓存的差异字段

    Returns:
        合并后的 settings（用户修改过的 settings）
    """
    if not cached_diff:
        # 没有差异，返回磁盘上的 settings
        return copy.deepcopy(disk_settings)

    return _deep_merge(disk_settings, cached_diff)


__all__ = [
    "FINGERPRINT_FIELDS",
    "NON_FINGERPRINT_FIELDS",
    "diff_settings",
    "filter_fingerprint_fields",
    "diff_and_filter",
    "merge_settings",
]