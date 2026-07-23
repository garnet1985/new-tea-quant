#!/usr/bin/env python3
"""Tag settings 规范化服务（单点声明，删除隐形转换）。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.modules.tag.models.tag_enums import TagTargetType, TagUpdateMode


def normalize_tag_settings(settings: Dict[str, Any], tag_key: str) -> Dict[str, Any]:
    """规范化 tag settings，返回标准化后的 settings dict。

    Args:
        settings: Raw settings dict（可能缺少字段或格式不规范）
        tag_key: Tag scenario key（用于定位 scenario）

    Returns:
        规范化后的 settings dict，包含所有必需字段和默认值

    流程：
    1. 验证必需字段（name, execution_mode, data）
    2. 规范化 execution_mode（默认 entity_timeline）
    3. 规范化 update_mode（默认 refresh）
    4. 规范化 data block（base + required + min_required_records）
    5. 从 base_required_data 获取 attach_to_data_key（单点声明）
    6. 自动填充 meta（避免重复声明）
    7. 删除 performance block（不需要）

    关键设计：
    - attach_to_data_key 直接使用 base_required_data.data_id（单点声明）
    - 不需要隐形转换（直接存储 DataKey，例如 "stock.kline.daily"）
    - 不需要用户显式声明 attach_to_data_key（避免配置不一致）
    """
    # 1. 验证必需字段
    settings = dict(settings or {})
    name = settings.get("name")
    if not name:
        settings["name"] = tag_key
    name = settings.get("name")
    if not isinstance(name, str) or not str(name).strip():
        raise ValueError("name 必填且须为 str")

    # 2. 规范化 execution_mode
    execution_mode = str(settings.get("execution_mode") or "").strip().lower()
    if not execution_mode:
        execution_mode = "entity_timeline"
    if execution_mode not in {"entity_timeline", "calendar_slice"}:
        raise ValueError(f"execution_mode 必须为 entity_timeline 或 calendar_slice，收到 {execution_mode!r}")
    settings["execution_mode"] = execution_mode

    # 3. 规范化 update_mode
    calculation = settings.get("calculation") or {}
    if not isinstance(calculation, dict):
        calculation = {}
    update_mode = str(calculation.get("update_mode") or "refresh").strip().lower()
    if update_mode not in {"refresh", "incremental"}:
        raise ValueError(f"update_mode 必须为 refresh 或 incremental，收到 {update_mode!r}")
    settings["update_mode"] = update_mode
    settings["recompute"] = bool(calculation.get("recompute", True))

    # 4. 规范化 data block
    data_block = settings.get("data")
    if not isinstance(data_block, dict):
        raise ValueError("data 须为 dict")
    expanded_data, min_records, base_id = _expand_data_block(data_block)
    settings["data"] = expanded_data
    settings["incremental_required_records_before_as_of_date"] = min_records
    settings["tag_target_type"] = TagTargetType.ENTITY_BASED.value

    # 5. 从 base_required_data 获取 attach_to_data_key（单点声明）
    # 直接使用 DataKey（例如 "stock.kline.daily"），不需要隐形转换
    attach_to_data_key = base_id  # 例如 "stock.kline.daily"
    settings["attach_to_data_key"] = attach_to_data_key

    # 自动填充 meta（避免重复声明）
    settings.setdefault("meta", {})
    settings["meta"]["attach_to_data_key"] = attach_to_data_key

    settings.pop("performance", None)
    settings.setdefault("run_options", {})

    return settings


def _expand_data_block(data_block: Dict[str, Any]) -> Tuple[Dict[str, Any], int, str]:
    """展开 data block，返回规范化后的 data dict。

    Args:
        data_block: Raw data block dict

    Returns:
        Tuple: (expanded_data, min_records, base_id)

    流程：
    1. 验证 base_required_data（必填）
    2. 规范化 extra_required_data_sources（可选）
    3. 计算 min_required_records
    4. 获取 base_id（直接使用 DataKey）
    5. 设置 tag_time_axis_based_on（用于 tag job）

    关键设计：
    - base_id 直接使用 DataKey（例如 "stock.kline.daily"）
    - 不需要隐形转换（直接存储 DataKey）
    - attach_to_data_key = base_id（单点声明）
    """
    if not isinstance(data_block, dict):
        raise ValueError("data_block 须为 dict")

    base_required_data = data_block.get("base_required_data")
    if not isinstance(base_required_data, dict):
        raise ValueError("data.base_required_data 必填且须为 dict")

    base_id = str(base_required_data.get("data_id") or "").strip()
    if not base_id:
        raise ValueError("data.base_required_data.data_id 必填")

    # 规范化 base_required_data
    normalized_base = {
        "data_id": base_id,
        "params": dict(base_required_data.get("params") or {}),
        "indicators": dict(base_required_data.get("indicators") or {}),
    }

    # 规范化 extra_required_data_sources
    extra_required_data_sources = data_block.get("extra_required_data_sources")
    if extra_required_data_sources is None:
        extra_required_data_sources = []
    elif not isinstance(extra_required_data_sources, list):
        raise ValueError("data.extra_required_data_sources 须为 list")

    normalized_required = []
    for index, item in enumerate(extra_required_data_sources):
        if not isinstance(item, dict):
            raise ValueError(f"data.extra_required_data_sources[{index}] 须为 dict")
        normalized_required.append(_normalize_required_item(item, label=f"data.extra_required_data_sources[{index}]"))

    # 合并 base 和 required（base 放在最前面）
    all_required = [normalized_base] + normalized_required

    # 计算 min_required_records
    min_required_records = data_block.get("min_required_records")
    if min_required_records is None:
        min_required_records = 20
    try:
        min_records = max(1, int(min_required_records))
    except (TypeError, ValueError):
        min_records = 20

    # 设置 tag_time_axis_based_on（用于 tag job）
    expanded_data = {
        "base_required_data": normalized_base,
        "required": all_required,
        "min_required_records": min_records,
        "tag_time_axis_based_on": base_id,  # tag 时间轴基于 base data（DataKey）
    }

    return expanded_data, min_records, base_id


def _normalize_required_item(item: Dict[str, Any], *, label: str = "data.required[]") -> Dict[str, Any]:
    """规范化单个 required data item。

    Args:
        item: Raw required data item dict
        label: Error message label（用于定位错误）

    Returns:
        规范化后的 required data item dict

    规范化字段：
    - data_id：必填，验证非空
    - params：可选，默认 {}
    - indicators：可选，默认 {}
    """
    data_id = str(item.get("data_id") or "").strip()
    if not data_id:
        raise ValueError(f"{label}.data_id 必填")

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
        "data_id": data_id,
        "params": dict(params),
        "indicators": dict(indicators),
    }


__all__ = ["normalize_tag_settings"]