#!/usr/bin/env python3
"""Tag settings 规范化服务（单点声明，删除隐形转换）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.data_contract import ContractIssuer, ContractType
from core.modules.tag.enums import TagExecutionMode, TagTargetType, TagUpdateMode

_issuer: Optional[ContractIssuer] = None


def _contract_issuer() -> ContractIssuer:
    global _issuer
    if _issuer is None:
        _issuer = ContractIssuer()
        _issuer.discover()
    return _issuer


def normalize_tag_settings(settings: Dict[str, Any], tag_key: str) -> Dict[str, Any]:
    """规范化 tag settings，返回标准化后的 settings dict。

    Userspace 契约见 ``userspace/extensions/tags/settings_example.py``。
    本函数将 calculation.execution / data.base / tag_definitions 等展开为
    引擎可读的扁平字段（execution_mode、start_date、data.required 等）。
    """
    settings = dict(settings or {})
    name = settings.get("name")
    if not name:
        settings["name"] = tag_key
    name = settings.get("name")
    if not isinstance(name, str) or not str(name).strip():
        raise ValueError("name 必填且须为 str")

    calculation = settings.get("calculation") or {}
    if not isinstance(calculation, dict):
        calculation = {}

    execution = calculation.get("execution") or {}
    if not isinstance(execution, dict):
        execution = {}

    execution_mode = str(execution.get("mode") or "").strip().lower()
    if not execution_mode:
        execution_mode = TagExecutionMode.ENTITY_BASED.value
    if execution_mode not in {x.value for x in TagExecutionMode}:
        raise ValueError(
            f"calculation.execution.mode 必须为 entity_based 或 slice_based，收到 {execution_mode!r}"
        )
    settings["execution_mode"] = execution_mode
    settings["start_date"] = str(execution.get("start_date") or "").strip()
    settings["end_date"] = str(execution.get("end_date") or "").strip()

    update_mode = str(calculation.get("update_mode") or TagUpdateMode.REFRESH.value).strip().lower()
    if update_mode not in {x.value for x in TagUpdateMode}:
        raise ValueError(f"update_mode 必须为 refresh 或 incremental，收到 {update_mode!r}")
    settings["update_mode"] = update_mode
    settings["recompute"] = bool(calculation.get("recompute", False))

    data_block = settings.get("data")
    if not isinstance(data_block, dict):
        raise ValueError("data 须为 dict")
    expanded_data, min_records, base_key = _expand_data_block(data_block)
    settings["data"] = expanded_data
    settings["incremental_required_records_before_as_of_date"] = min_records
    settings["tag_target_type"] = TagTargetType.ENTITY_BASED.value
    settings["attach_to_data_key"] = base_key
    settings["target_entity"] = {"type": base_key.replace(".", "_")}

    meta = settings.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        settings["meta"] = meta
    meta["attach_to_data_key"] = base_key
    if not str(meta.get("key") or "").strip():
        meta["key"] = str(tag_key).strip()

    tag_definitions = settings.get("tag_definitions")
    if tag_definitions is None:
        raise ValueError("tag_definitions 必填且须为非空 list")
    if not isinstance(tag_definitions, list):
        raise ValueError("tag_definitions 须为 list")
    settings["tag_definitions"] = tag_definitions

    settings.pop("performance", None)
    settings.setdefault("run_options", {})

    return settings


def _expand_data_block(data_block: Dict[str, Any]) -> Tuple[Dict[str, Any], int, str]:
    """展开 data block：base + required → 引擎用 data.required。"""
    if not isinstance(data_block, dict):
        raise ValueError("data_block 须为 dict")

    base = data_block.get("base")
    if not isinstance(base, dict):
        raise ValueError("data.base 必填且须为 dict")

    base_key = str(base.get("data_key") or "").strip()
    if not base_key:
        raise ValueError("data.base.data_key 必填")

    normalized_base = {
        "data_key": base_key,
        "params": dict(base.get("params") or {}),
        "indicators": dict(base.get("indicators") or {}),
    }

    required_raw = data_block.get("required")
    if required_raw is None:
        required_raw = []
    elif not isinstance(required_raw, list):
        raise ValueError("data.required 须为 list")

    normalized_required: List[Dict[str, Any]] = []
    for index, item in enumerate(required_raw):
        if not isinstance(item, dict):
            raise ValueError(f"data.required[{index}] 须为 dict")
        normalized_required.append(
            _normalize_required_item(item, label=f"data.required[{index}]")
        )

    all_required = [normalized_base] + normalized_required

    min_required_records = data_block.get("min_required_records")
    if min_required_records is None:
        min_records = 0
    else:
        try:
            min_records = max(0, int(min_required_records))
        except (TypeError, ValueError):
            min_records = 0

    axis = _resolve_time_axis(all_required, preferred=base_key)
    expanded_data = {
        "base": normalized_base,
        "required": all_required,
        "min_required_records": min_records,
        "tag_time_axis_based_on": axis,
    }

    return expanded_data, min_records, base_key


def _resolve_time_axis(all_required: List[Dict[str, Any]], *, preferred: str) -> str:
    """时间轴：优先 base（若为时序），否则第一个时序 data_key。"""
    preferred_key = str(preferred or "").strip()
    if preferred_key and _is_time_series(preferred_key):
        return preferred_key
    for item in all_required:
        key = str(item.get("data_key") or "").strip()
        if key and _is_time_series(key):
            return key
    return preferred_key


def _declaration_meta(data_key: str) -> Optional[Dict[str, Any]]:
    decl = _contract_issuer().get_declaration(str(data_key or "").strip())
    if not isinstance(decl, dict):
        return None
    meta = decl.get("meta")
    return meta if isinstance(meta, dict) else None


def _is_time_series(data_key: str) -> bool:
    meta = _declaration_meta(data_key)
    if not meta:
        return False
    return str(meta.get("type") or "").strip().lower() == ContractType.TIME_SERIES


def _normalize_required_item(item: Dict[str, Any], *, label: str = "data.required[]") -> Dict[str, Any]:
    data_key = str(item.get("data_key") or "").strip()
    if not data_key:
        raise ValueError(f"{label}.data_key 必填")

    params = item.get("params")
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        raise ValueError(f"{label}.params 必须为 dict")

    indicators = item.get("indicators")
    if indicators is None:
        indicators = {}
    elif not isinstance(indicators, dict):
        raise ValueError(f"{label}.indicators 必须为 dict")

    return {
        "data_key": data_key,
        "params": dict(params),
        "indicators": dict(indicators),
    }


def declaration_data_key(item: Optional[Dict[str, Any]]) -> str:
    """从声明项读取 data_key（规范化后唯一字段）。"""
    if not isinstance(item, dict):
        return ""
    return str(item.get("data_key") or "").strip()


__all__ = ["normalize_tag_settings", "declaration_data_key"]
