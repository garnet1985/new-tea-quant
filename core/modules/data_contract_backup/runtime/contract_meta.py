"""
从 **规则类** `BaseContract` 实例生成可序列化的 **meta 快照**，写入 `DataEntity.meta`。

句柄 issue 阶段不拉数，只把「已定稿的形态」固化进句柄，供 load / 校验 / 缓存键使用。
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from core.modules.data_contract.contracts import BaseContract


def build_rule_meta(contract: BaseContract) -> Mapping[str, Any]:
    """
    提取规则类上影响「形态」的字段；**不包含**大数据主体。

    字段集随具体子类扩展；未知属性通过 `dataclasses.fields` 遍历可演进，当前用显式白名单保持可读。
    """
    meta: Dict[str, Any] = {
        "contract_id": contract.contract_id,
        "name": contract.name,
        "scope": contract.scope.value,
        "rule_class": type(contract).__name__,
    }
    if getattr(contract, "display_name", None):
        meta["display_name"] = contract.display_name
    ctx = getattr(contract, "context", None)
    if ctx:
        meta["rule_context"] = dict(ctx)

    for attr in ("time_axis_field", "required_fields", "context_entity_id_key"):
        if not hasattr(contract, attr):
            continue
        val = getattr(contract, attr)
        if attr == "required_fields" and val is not None:
            meta[attr] = tuple(val)
        else:
            meta[attr] = val

    return meta
