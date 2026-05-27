"""stock_list 维度字段须在 normalize 裁剪前可从映射记录中读出（不依赖 userspace / DB）。"""
from core.modules.data_source.service.utils.stock_list_dimension_values import (
    group_stock_list_dimension_values,
)


def test_group_dimension_values_from_mapped_record():
    raw = [
        {
            "id": "000001.SZ",
            "name": "平安银行",
            "industry": "银行",
            "board": "主板",
            "market": "SZSE",
            "area": "深圳",
        }
    ]
    boards, markets, industries, areas = group_stock_list_dimension_values(raw)
    assert boards == ["主板"]
    assert markets == ["SZSE"]
    assert industries == ["银行"]
    assert areas == ["深圳"]
