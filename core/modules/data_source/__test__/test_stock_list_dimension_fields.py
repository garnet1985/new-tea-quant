"""stock_list 维度字段须在 on_after_mapping 前保留（不依赖 DB）。"""
from userspace.data_source.handlers.stock_list.handler import TushareStockListHandler


def test_group_dimension_values_from_mapped_record():
    handler = TushareStockListHandler.__new__(TushareStockListHandler)
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
    boards, markets, industries, areas = handler._group_dimension_values(raw)
    assert boards == ["主板"]
    assert markets == ["SZSE"]
    assert industries == ["银行"]
    assert areas == ["深圳"]
