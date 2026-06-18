"""worker_exec 单元测试。"""
from __future__ import annotations

from core.modules.tag.engines.shared.worker_exec import entity_sub_payload


def test_entity_sub_payload_includes_worker_file_path():
    payload = {
        "entity_type": "stock_kline_daily",
        "scenario_name": "demo/market_cap_tier",
        "worker_module_path": "_ntq_tag_worker_demo_market_cap_tier",
        "worker_class_name": "MarketCapTierTagWorker",
        "worker_file_path": "/tmp/demo/market_cap_tier/tag_worker.py",
        "settings": {},
    }
    sub = entity_sub_payload(
        payload,
        {"entity_id": "000001.SZ", "start_date": "20240101", "end_date": "20240131"},
        {"slot_data": {}},
    )
    assert sub["worker_file_path"] == "/tmp/demo/market_cap_tier/tag_worker.py"
    assert sub["entity_id"] == "000001.SZ"
