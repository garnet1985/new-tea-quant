"""Tag Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .contract import TagContract
from .loader import TagLoader


TAG_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.TAG,
        "type": "time_series",  # 默认值（实际由 scenario 决定）
        "scope": "per_entity",  # 默认值（实际由 scenario 决定）
        # 默认股票池；实际实体族由 scenario.attach_to / data.base 决定
        "list_data_key": SYS_DATA_KEY.STOCK_LIST,
        "display_name": "特征标签（按场景）",
        "description": "特征标签数据，需要 scenario 参数才能加载",
        "unique_keys": ["entity_id", "tag_definition_id", "as_of_date"],
        "contract_class": TagContract,
        "loader": TagLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {
        # 落库与 loader 使用 as_of_date；until / 切片须认这个字段，不能默认 date
        "time_axis_field": "as_of_date",
    },
}


__all__ = ['TAG_DECLARATION']
