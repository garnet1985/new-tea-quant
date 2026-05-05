#!/usr/bin/env python3
"""
**Settings 步骤层**：``raw_settings`` → 指纹与持久化共用的 **校验通过 + 规范化完整快照**；

以及对校验后快照做 **语义剔除**（不参与 ``settings_fp`` 哈希的键），规则见
``core/modules/strategy/docs/settings-fingerprint-policy.md``。
本模块只做 **数据收集与组装**（规范化快照、语义核 dict）；**SHA256** 由 ``finger_print`` 模块负责。
"""

from __future__ import annotations

import copy
from typing import Any, Dict, FrozenSet, Optional, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)


def _require_valid_snapshot(settings: StrategySettings) -> Dict[str, Any]:
    """validate() 通过后返回 ``to_dict()``；否则 ``ValueError``。"""
    if not isinstance(settings, StrategySettings):
        raise TypeError("expected StrategySettings")
    report = settings.validate()
    if report.is_usable():
        return settings.to_dict()
    errs = [
        f'{item.get("field_path", "?")}: {item.get("message", "")}'
        for item in (report.errors or [])
        if item.get("level") == "critical"
    ]
    detail = "；".join(errs) if errs else "settings 校验未通过"
    raise ValueError(detail)


def semantic_core(raw_settings: Dict[str, Any]) -> Dict[str, Any]:
    """原始 settings dict → 校验通过 → 剔除非语义字段 → **语义核 dict**（供 ``finger_print.to_settings_hash`` 使用）。"""
    inst = StrategySettings(raw_settings=dict(raw_settings or {}))
    return strip_to_semantic_core(_require_valid_snapshot(inst))


def semantic_core_from_strategy_settings(settings: StrategySettings) -> Dict[str, Any]:
    """已有 ``StrategySettings`` 实例 → 语义核 dict（供列指纹哈希输入）。"""
    return strip_to_semantic_core(_require_valid_snapshot(settings))


# --- semantic core strip（指纹哈希用；常量仅本模块使用）-------------------------------------------

_IGNORE_ROOT_KEYS: FrozenSet[str] = frozenset(
    {
        "description",
        "is_enabled",
        "meta",
    }
)

_DROP_ROOT_BLOCKS: FrozenSet[str] = frozenset({"scanner"})

_IGNORE_ENUMERATOR_KEYS: FrozenSet[str] = frozenset(
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

_IGNORE_PRICE_SIMULATOR_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "use_sampling",
        "start_date",
        "end_date",
        "fees",
    }
)

_IGNORE_CAPITAL_SIMULATOR_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "use_sampling",
        "start_date",
        "end_date",
        "fees",
    }
)

_IGNORE_CAPITAL_OUTPUT_KEYS: FrozenSet[str] = frozenset(
    {
        "save_trades",
        "save_equity_curve",
    }
)


def resolve_sampling_is_used(settings: Dict[str, Any]) -> bool:
    """是否启用采样选股（仅看 sampling.use_sampling）。"""
    s = settings.get("sampling")
    return isinstance(s, dict) and bool(s.get("use_sampling", False))


def _strip_to_semantic_core(canonical_settings: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(canonical_settings)
    sampling_used = resolve_sampling_is_used(out)

    for block in _DROP_ROOT_BLOCKS:
        out.pop(block, None)

    for key in _IGNORE_ROOT_KEYS:
        out.pop(key, None)

    enum_block = dict(out.get("enumerator") or {})
    for key in _IGNORE_ENUMERATOR_KEYS:
        enum_block.pop(key, None)
    out["enumerator"] = enum_block

    ps_block = dict(out.get("price_simulator") or {})
    for key in _IGNORE_PRICE_SIMULATOR_KEYS:
        ps_block.pop(key, None)
    out["price_simulator"] = ps_block

    cs_block = dict(out.get("capital_simulator") or {})
    for key in _IGNORE_CAPITAL_SIMULATOR_KEYS:
        cs_block.pop(key, None)

    out_cap_output = cs_block.get("output")
    if isinstance(out_cap_output, dict):
        od = dict(out_cap_output)
        for key in _IGNORE_CAPITAL_OUTPUT_KEYS:
            od.pop(key, None)
        if od:
            cs_block["output"] = od
        else:
            cs_block.pop("output", None)
    out["capital_simulator"] = cs_block

    if not sampling_used:
        out.pop("sampling", None)

    return out


def strip_to_semantic_core(canonical_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    输入须为 ``StrategySettings.validate()`` 后 ``to_dict()`` 的完整快照。
    返回用于指纹哈希的语义核 dict。
    """
    return _strip_to_semantic_core(canonical_settings)


# --- normalized snapshot（持久化 / 下游完整 dict）----------------------------------------------------

def validated_normalized_snapshot(
    raw_settings: Dict[str, Any],
) -> Optional[Tuple[StrategySettings, Dict[str, Any]]]:
    """
    ``raw_settings`` → ``StrategySettings``；校验 ``report.is_usable()`` 通过后 ``to_dict()``，
    得到与 **settings 指纹 / 表 settings_snapshot** 同源的完整快照 dict。

    不可用或非 dict 时 ``None``（等价于原先对 ``ValueError`` 的捕获）。
    """
    # ``StrategySettings``：把 dict 解析成 meta/data/goal 等结构化字段，并提供 ``validate`` / ``to_dict``。
    validated = StrategySettings(raw_settings=dict(raw_settings or {}))
    # ``ValidationReport``（``SettingsBase``）：汇总校验错误；``is_usable()`` 表示无 critical、可做后续指纹/落库。
    report = validated.validate()
    if not report.is_usable():
        return None
    normalized = validated.to_dict()
    if not isinstance(normalized, dict):
        return None
    return validated, normalized


__all__ = [
    "resolve_sampling_is_used",
    "semantic_core",
    "semantic_core_from_strategy_settings",
    "strip_to_semantic_core",
    "validated_normalized_snapshot",
]
