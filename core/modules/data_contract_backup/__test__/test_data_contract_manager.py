"""
DataContractManager 单元测试（MVP 路由 + validate_raw / issue_handle）
"""

try:
    import pytest
except ImportError:
    pytest = None

from core.modules.data_contract import DataContractManager, DataKey, ResolverRegistry, TAG_KIND_CONTEXT_KEY
from core.modules.data_contract.contracts import ContractScope


class TestDataContractManager:
    def test_resolve_kline_contract(self):
        m = DataContractManager()
        c = m.resolve_contract(DataKey.STOCK_KLINE_DAILY_QFQ)
        assert c.scope == ContractScope.PER_ENTITY
        assert c.time_axis_field == "date"

    def test_issue_kline_ok(self):
        m = DataContractManager()
        raw = [{"date": "20240101", "open": 1, "high": 2, "low": 0.5, "close": 1.5}]
        out = m.validate_raw(
            DataKey.STOCK_KLINE_DAILY_QFQ,
            raw,
            context={"entity_id": "600000.SH"},
        )
        assert out == raw

    def test_issue_global_static(self):
        m = DataContractManager()
        raw = {"a": 1}
        out = m.validate_raw(DataKey.STOCK_LIST, raw)
        assert out == raw

    def test_tag_scenario_eventlog_vs_category(self):
        m = DataContractManager()
        rows = [{"as_of_date": "20240101", "v": 1}]
        out_ev = m.validate_raw(
            DataKey.TAG_SCENARIO,
            rows,
            context={"entity_id": "x", TAG_KIND_CONTEXT_KEY: "eventlog"},
        )
        assert out_ev == rows

        out_cat = m.validate_raw(
            DataKey.TAG_SCENARIO,
            {"k": 1},
            context={"entity_id": "x", TAG_KIND_CONTEXT_KEY: "category"},
        )
        assert out_cat == {"k": 1}

    def test_issue_handle_then_load(self):
        m = DataContractManager()
        h = m.issue_handle(
            DataKey.STOCK_LIST,
            params={"mode": "snapshot"},
            context=None,
        )
        assert h.data_id == DataKey.STOCK_LIST.value
        assert h.meta.get("scope") == "global"

        reg = ResolverRegistry()

        def _resolver(entity, **kwargs):
            assert entity.data_id == DataKey.STOCK_LIST.value
            return {"ok": True, "kwargs": kwargs}

        reg.register(DataKey.STOCK_LIST.value, _resolver)
        out = h.load(reg, foo=1)
        assert out == {"ok": True, "kwargs": {"foo": 1}}
        assert h.loaded == out
