"""Tag Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .contract import TagContract


TAG_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.TAG,
        "type": "time_series",  # 默认值（实际由 scenario 决定）
        "scope": "per_entity",  # 默认值（实际由 scenario 决定）
        "display_name": "特征标签（按场景）",
        "description": "特征标签数据，需要 scenario 参数才能加载",
        "unique_keys": ["entity_id", "tag_definition_id", "as_of_date"],
        "contract_class": TagContract,  # 使用自定义 Contract 类
        # loader 由 TagContract 内部处理
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['TAG_DECLARATION']