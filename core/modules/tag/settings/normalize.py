#!/usr/bin/env python3
"""Tag settings 规范化：userspace schema → 引擎内部形态。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from core.infra.job_pipeline.profile import WorkerProfiles, profile_dispatch_config
from core.infra.job_pipeline.profile.resolver import resolve_worker_profile
from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.mapping import default_map
from core.modules.data_contract.tag_entity_type import resolve_tag_entity_type
from core.modules.tag.enums import TagTargetType

def profile_tag_runtime_config() -> Dict[str, Any]:
    """``worker.json`` → ``job_pipeline.tag`` 下的调度默认值（不含业务 update_mode）。"""
    defaults: Dict[str, Any] = {
        "entities_per_job": "auto",
        "dispatch_probe": True,
        "stage_in_worker": True,
        "data_chunk_size": 500,
        "memory_floor_mb": "auto",
    }
    prof = resolve_worker_profile(WorkerProfiles.TAG)
    runtime = prof.get("runtime")
    if isinstance(runtime, dict):
        for key, value in runtime.items():
            if key != "update_mode":
                defaults[key] = value
    dispatch = profile_dispatch_config(WorkerProfiles.TAG)
    if dispatch:
        defaults.update(dispatch)
    return defaults


def _source_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    data_id = str(item.get("data_id") or "").strip()
    if not data_id:
        raise ValueError("data 源声明缺少 data_id")
    out: Dict[str, Any] = {
        "data_id": data_id,
        "params": dict(item.get("params") or {}),
    }
    indicators = item.get("indicators")
    if isinstance(indicators, dict) and indicators:
        out["indicators"] = indicators
    return out


def _resolve_entity_type(data_id: str) -> str:
    return resolve_tag_entity_type(data_id)


def _expand_data_block(data_block: Dict[str, Any]) -> Dict[str, Any]:
    base_raw = data_block.get("base_required_data")
    if not isinstance(base_raw, dict):
        raise ValueError("data.base_required_data 必填且须为 dict")

    base = _source_entry(base_raw)
    base_id = base["data_id"]
    try:
        base_dk = DataKey(base_id)
    except ValueError as exc:
        raise ValueError(f"data.base_required_data.data_id 不合法: {base_id!r}") from exc
    base_spec = default_map.get(base_dk)
    if base_spec is None:
        raise ValueError(f"data.base_required_data.data_id 未注册: {base_id!r}")
    if base_spec.get("scope") != ContractScope.PER_ENTITY:
        raise ValueError(
            f"data.base_required_data.data_id={base_id!r} 须为 PER_ENTITY 时序源"
        )
    if base_spec.get("type") != ContractType.TIME_SERIES:
        raise ValueError(
            f"data.base_required_data.data_id={base_id!r} 须为 TIME_SERIES 时序源"
        )

    extra_raw = data_block.get("extra_required_data_sources")
    if extra_raw is None:
        extra_raw = []
    if not isinstance(extra_raw, list):
        raise ValueError("data.extra_required_data_sources 须为 list")

    required: List[Dict[str, Any]] = [base]
    seen = {base_id}
    for i, item in enumerate(extra_raw):
        if not isinstance(item, dict):
            raise ValueError(f"data.extra_required_data_sources[{i}] 须为 dict")
        entry = _source_entry(item)
        eid = entry["data_id"]
        if eid in seen:
            raise ValueError(f"data 声明出现重复 data_id: {eid}")
        seen.add(eid)
        required.append(entry)

    min_records = data_block.get("min_required_records", 0)
    try:
        min_records_int = int(min_records)
    except (TypeError, ValueError) as exc:
        raise ValueError("data.min_required_records 须为非负整数") from exc
    if min_records_int < 0:
        raise ValueError("data.min_required_records 须为非负整数")

    expanded = dict(data_block)
    expanded["required"] = required
    expanded["tag_time_axis_based_on"] = base_id
    return expanded, min_records_int, _resolve_entity_type(base_id)


def _expand_calculation_block(calculation: Dict[str, Any]) -> Dict[str, Any]:
    update_mode = str(calculation.get("update_mode") or "incremental").strip().lower()
    execution_mode = str(calculation.get("execution_mode") or "entity_timeline").strip().lower()
    return {
        "update_mode": update_mode,
        "execution_mode": execution_mode,
        "recompute": bool(calculation.get("recompute", False)),
        "start_date": calculation.get("start_date", "") or "",
        "end_date": calculation.get("end_date", "") or "",
    }


def normalize_tag_settings(
    raw: Dict[str, Any],
    *,
    tag_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    将 userspace settings（``settings_example.py`` schema）规范化为引擎内部形态。

    userspace 必填：``data.base_required_data``、``tags``；
    ``name`` 由 discovery 注入 ``tag_key``。
    """
    settings = deepcopy(raw or {})
    key = str(tag_key or "").strip()
    if not key:
        raise ValueError("tag_key 不能为空")
    settings["name"] = key

    meta = settings.get("meta")
    if not isinstance(meta, dict):
        settings["meta"] = {}

    calculation_raw = settings.get("calculation")
    if calculation_raw is None:
        calculation_raw = {}
    if not isinstance(calculation_raw, dict):
        raise ValueError("calculation 须为 dict")
    calc = _expand_calculation_block(calculation_raw)
    settings["execution_mode"] = calc["execution_mode"]
    settings["recompute"] = calc["recompute"]
    settings["start_date"] = calc["start_date"]
    settings["end_date"] = calc["end_date"]

    data_block = settings.get("data")
    if not isinstance(data_block, dict):
        raise ValueError("data 须为 dict")
    expanded_data, min_records, entity_type = _expand_data_block(data_block)
    settings["data"] = expanded_data
    settings["incremental_required_records_before_as_of_date"] = min_records
    settings["tag_target_type"] = TagTargetType.ENTITY_BASED.value
    settings["target_entity"] = {"type": entity_type}

    performance = settings.get("performance")
    explicit_performance_keys: list[str] = []
    if isinstance(performance, dict):
        explicit_performance_keys = list(performance.keys())
    global_perf = profile_tag_runtime_config()
    settings["performance"] = {
        **global_perf,
        **(performance if isinstance(performance, dict) else {}),
        "update_mode": calc["update_mode"],
    }
    if explicit_performance_keys:
        settings["_explicit_performance_keys"] = explicit_performance_keys

    return settings


__all__ = ["normalize_tag_settings", "profile_tag_runtime_config"]
