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
        "max_parallel_jobs_cap",
        "is_verbose",
        "memory_budget_mb",
        "memory_floor_mb",
        "main_process_reserve_mb",
        "warmup_batch_size",
        "min_batch_size",
        "max_batch_size",
        "monitor_interval",
        "entities_per_job",
        "entities_per_job_min",
        "entities_per_job_max",
        "dispatch_probe",
        "dispatch_probe_entities",
        "dispatch_probe_safety_factor",
        "mb_per_entity_staged",
        "worker_memory_fraction",
        "prefetch_ahead",
        "max_test_versions",
    }
)

# 保留策略不参与 settings 语义指纹（改保留份数不应导致缓存失效）
_IGNORE_SIMULATION_RETENTION_KEYS: FrozenSet[str] = frozenset(
    {
        "max_output_versions",
        "max_workbench_versions",
    }
)

_IGNORE_PRICE_SIMULATOR_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "max_parallel_jobs_cap",
        "entities_per_job",
        "dispatch_probe",
        "dispatch_probe_entities",
        "dispatch_probe_safety_factor",
        "sec_per_entity_staged",
        "sec_per_job_overhead_staged",
        "force_main_process",
        "start_date",
        "end_date",
    }
)

_IGNORE_CAPITAL_SIMULATOR_KEYS: FrozenSet[str] = frozenset(
    {
        "max_workers",
        "max_parallel_jobs_cap",
        "start_date",
        "end_date",
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


def coerce_numeric_tree_for_fingerprint(value: Any) -> Any:
    """
    指纹 / 持久化快照用：``int`` 与 ``float`` 在数值相等时规范为 ``float``，
    避免 UI JSON（整数）与 CLI ``settings.py``（浮点）产生不同 ``settings_fp``。
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, dict):
        return {k: coerce_numeric_tree_for_fingerprint(v) for k, v in value.items()}
    if isinstance(value, list):
        return [coerce_numeric_tree_for_fingerprint(v) for v in value]
    return value


def _strip_to_semantic_core(canonical_settings: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(canonical_settings)

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

    # ``sampling`` 块：根据 ``use_sampling`` 决定是否剔除采样配置
    # - use_sampling=False：只保留 use_sampling，剔除其他采样配置（pool.file 等）
    # - use_sampling=True：保留整个 sampling 块（pool.file 等参与指纹）
    sampling_block = dict(out.get("sampling") or {})
    use_sampling = bool(sampling_block.get("use_sampling", False))
    if not use_sampling:
        # 非采样模式：只保留 use_sampling 字段
        sampling_block = {"use_sampling": False}
    out["sampling"] = sampling_block

    # goal 块：剔除展示字段 name（不影响回测结果）
    goal_block = dict(out.get("goal") or {})
    # 剔除 stop_loss.stages[].name
    stop_loss = goal_block.get("stop_loss")
    if isinstance(stop_loss, dict):
        stages = stop_loss.get("stages")
        if isinstance(stages, list):
            for stage in stages:
                if isinstance(stage, dict):
                    stage.pop("name", None)
    # 剔除 take_profit.stages[].name
    take_profit = goal_block.get("take_profit")
    if isinstance(take_profit, dict):
        stages = take_profit.get("stages")
        if isinstance(stages, list):
            for stage in stages:
                if isinstance(stage, dict):
                    stage.pop("name", None)
    # 剔除 stock_status_risk_management.rules[].name
    risk_mgmt = goal_block.get("stock_status_risk_management")
    if isinstance(risk_mgmt, dict):
        rules = risk_mgmt.get("rules")
        if isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, dict):
                    rule.pop("name", None)
    out["goal"] = goal_block

    sim_block = dict(out.get("simulation") or {})
    ret_block = dict(sim_block.get("retention") or {})
    for key in _IGNORE_SIMULATION_RETENTION_KEYS:
        ret_block.pop(key, None)
    if ret_block:
        sim_block["retention"] = ret_block
    else:
        sim_block.pop("retention", None)
    if sim_block:
        out["simulation"] = sim_block
    else:
        out.pop("simulation", None)

    return coerce_numeric_tree_for_fingerprint(out)


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
    return validated, coerce_numeric_tree_for_fingerprint(normalized)


__all__ = [
    "coerce_numeric_tree_for_fingerprint",
    "resolve_sampling_is_used",
    "semantic_core",
    "semantic_core_from_strategy_settings",
    "strip_to_semantic_core",
    "validated_normalized_snapshot",
]
