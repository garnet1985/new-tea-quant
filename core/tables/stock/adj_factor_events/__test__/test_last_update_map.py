"""adj_factor_events last_update 聚合查询。"""
from unittest.mock import MagicMock

from core.tables.stock.adj_factor_events.model import DataAdjFactorEventModel


def test_load_stock_last_update_map():
    db = MagicMock()
    db.execute_sync_query.return_value = [
        {"id": "000001.SZ", "last_update": "2025-06-09 10:00:00"},
        {"id": "000002.SZ", "last_update": "2025-06-08 09:00:00"},
    ]
    model = DataAdjFactorEventModel(db=db)
    m = model.load_stock_last_update_map()
    assert m["000001.SZ"] == "2025-06-09 10:00:00"
    assert m["000002.SZ"] == "2025-06-08 09:00:00"
