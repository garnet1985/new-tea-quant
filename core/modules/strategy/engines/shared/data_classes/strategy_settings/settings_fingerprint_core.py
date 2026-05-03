#!/usr/bin/env python3
"""
Settings 指纹：在 **已 canonical** 的 settings 上剔除不参与语义哈希的键。

流程：`StrategySettings.validate()` + `to_dict()` → `strip_fingerprint_non_core(...)`。

忽略表按块维护，新增业务字段默认参与哈希；仅当字段明确属于「性能 / 磁盘 / 展示」时再列入忽略。
参见 core/modules/strategy/docs/settings-fingerprint-policy.md。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, FrozenSet

# 根级：不参与枚举 / 工作台语义哈希
IGNORE_ROOT_KEYS: FrozenSet[str] = frozenset(
    {
        "description",
        "is_enabled",
        "meta",
    }
)

# 整块删除（与扫描流水线相关，与三步回测数值无关）
DROP_ROOT_BLOCKS: FrozenSet[str] = frozenset({"scanner"})

# enumerator：运行时 / 磁盘版本上限 / 采样路径遗留键（语义在 sampling.*）
IGNORE_ENUMERATOR_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "is_verbose",
        "memory_budget_mb",
        "warmup_batch_size",
        "min_batch_size",
        "max_batch_size",
        "monitor_interval",
        "max_test_versions",
        "max_output_versions",
        "use_sampling",
    }
)

IGNORE_PRICE_SIMULATOR_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "use_sampling",
        "start_date",
        "end_date",
        "fees",
    }
)

IGNORE_CAPITAL_SIMULATOR_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "use_sampling",
        "start_date",
        "end_date",
        "fees",
    }
)

# capital_simulator.output：仅落盘开关，默认不影响同一口径下的数值摘要
IGNORE_CAPITAL_OUTPUT_KEYS: FrozenSet[str] = frozenset(
    {
        "save_trades",
        "save_equity_curve",
    }
)


def resolve_sampling_is_used(settings: Dict[str, Any]) -> bool:
    """是否启用采样选股（仅看 sampling.use_sampling）。"""
    s = settings.get("sampling")
    return isinstance(s, dict) and bool(s.get("use_sampling", False))


def strip_fingerprint_non_core(canonical_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    输入须为 `StrategySettings.validate()` 后 `to_dict()` 的完整快照。
    返回用于指纹哈希的 settings_core（剔除忽略键与整块）。
    """
    out = copy.deepcopy(canonical_settings)
    sampling_used = resolve_sampling_is_used(out)

    for block in DROP_ROOT_BLOCKS:
        out.pop(block, None)

    for key in IGNORE_ROOT_KEYS:
        out.pop(key, None)

    enum_block = dict(out.get("enumerator") or {})
    for key in IGNORE_ENUMERATOR_KEYS:
        enum_block.pop(key, None)
    out["enumerator"] = enum_block

    ps_block = dict(out.get("price_simulator") or {})
    for key in IGNORE_PRICE_SIMULATOR_KEYS:
        ps_block.pop(key, None)
    out["price_simulator"] = ps_block

    cs_block = dict(out.get("capital_simulator") or {})
    for key in IGNORE_CAPITAL_SIMULATOR_KEYS:
        cs_block.pop(key, None)

    out_cap_output = cs_block.get("output")
    if isinstance(out_cap_output, dict):
        od = dict(out_cap_output)
        for key in IGNORE_CAPITAL_OUTPUT_KEYS:
            od.pop(key, None)
        if od:
            cs_block["output"] = od
        else:
            cs_block.pop("output", None)
    out["capital_simulator"] = cs_block

    if not sampling_used:
        out.pop("sampling", None)

    return out


__all__ = [
    "IGNORE_CAPITAL_OUTPUT_KEYS",
    "IGNORE_CAPITAL_SIMULATOR_KEYS",
    "IGNORE_ENUMERATOR_KEYS",
    "IGNORE_PRICE_SIMULATOR_KEYS",
    "IGNORE_ROOT_KEYS",
    "DROP_ROOT_BLOCKS",
    "resolve_sampling_is_used",
    "strip_fingerprint_non_core",
]
