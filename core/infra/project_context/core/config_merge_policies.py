#!/usr/bin/env python3
"""
可复用的配置合并策略（供 layered config 加载时传入 ``merge_fn``）。

各业务模块的 JSON 形状不同，合并语义在此按策略集中维护。
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def merge_market_profile_dicts(
    core: Dict[str, Any],
    user: Dict[str, Any],
) -> Dict[str, Any]:
    """合并 market profile：``rules.<type>.rules[]`` 按条目 ``key`` 合并。"""
    merged = copy.deepcopy(core)
    for key, user_val in user.items():
        if key == "rules":
            if not isinstance(user_val, dict):
                merged["rules"] = copy.deepcopy(user_val)
                continue
            core_rules = merged.get("rules")
            if not isinstance(core_rules, dict):
                merged["rules"] = copy.deepcopy(user_val)
                continue
            merged["rules"] = _merge_rules_map(core_rules, user_val)
            continue

        if isinstance(user_val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_nested_dict(merged[key], user_val)
        else:
            merged[key] = copy.deepcopy(user_val)
    return merged


def _merge_rules_map(
    core_rules: Dict[str, Any],
    user_rules: Dict[str, Any],
) -> Dict[str, Any]:
    out = copy.deepcopy(core_rules)
    for rule_type, user_block in user_rules.items():
        if not isinstance(user_block, dict):
            out[rule_type] = copy.deepcopy(user_block)
            continue
        core_block = out.get(rule_type)
        if isinstance(core_block, dict):
            out[rule_type] = _merge_rule_block(core_block, user_block)
        else:
            out[rule_type] = copy.deepcopy(user_block)
    return out


def _merge_rule_block(
    core_block: Dict[str, Any],
    user_block: Dict[str, Any],
) -> Dict[str, Any]:
    merged = copy.deepcopy(core_block)
    user_list = user_block.get("rules") if isinstance(user_block.get("rules"), list) else None

    for key, val in user_block.items():
        if key == "rules":
            continue
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_nested_dict(merged[key], val)
        else:
            merged[key] = copy.deepcopy(val)

    if user_list is not None:
        core_list = merged.get("rules")
        if isinstance(core_list, list):
            merged["rules"] = _merge_rule_entries_by_key(core_list, user_list)
        else:
            merged["rules"] = copy.deepcopy(user_list)
    return merged


def _merge_rule_entries_by_key(
    core_entries: List[Any],
    user_entries: List[Any],
) -> List[Dict[str, Any]]:
    by_key: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for item in core_entries:
        if not isinstance(item, dict):
            continue
        entry_key = str(item.get("key") or "").strip()
        if not entry_key:
            continue
        by_key[entry_key] = copy.deepcopy(item)
        order.append(entry_key)

    for item in user_entries:
        if not isinstance(item, dict):
            continue
        entry_key = str(item.get("key") or "").strip()
        if not entry_key:
            logger.warning("layered config 规则条目缺少 key，已跳过: %s", item)
            continue
        if entry_key in by_key:
            by_key[entry_key] = _merge_nested_dict(by_key[entry_key], item)
        else:
            by_key[entry_key] = copy.deepcopy(item)
            order.append(entry_key)

    return [by_key[k] for k in order if k in by_key]


def _merge_nested_dict(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_nested_dict(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


__all__ = ["merge_market_profile_dicts"]
