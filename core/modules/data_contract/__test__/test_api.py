"""公开 API 契约测 — ContractIssuer.issue / 包根导出（对齐 API.md）。"""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.force_run

from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import (
    BaseDataContract,
    BaseTimeSeriesContract,
    ContractScope,
    DATA_KEY,
)


class TestContractIssuerIssue:
    """测试 ContractIssuer.issue 静态签发。"""

    def test_package_exports_issuer_only(self):
        import core.modules.data_contract as pkg

        assert pkg.__all__ == ["ContractIssuer"]
        assert not hasattr(pkg, "DATA_KEY")

    def test_issue_global_without_fill(self):
        contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=False)
        assert isinstance(contract, BaseDataContract)
        assert contract.meta.key == DATA_KEY.STOCK_LIST
        assert contract.meta.scope == ContractScope.GLOBAL
        assert contract.is_loaded is False

    def test_issue_per_entity_with_runtime_no_fill(self):
        contract = ContractIssuer.issue(
            DATA_KEY.STOCK_KLINE_DAILY,
            entity_ids=["600000.SH"],
            runtime={"start_time": "20200101", "end_time": "20201231", "adjust": "qfq"},
            fill_in_data=False,
        )
        assert isinstance(contract, BaseTimeSeriesContract)
        assert contract.meta.key == DATA_KEY.STOCK_KLINE_DAILY
        # fill_in_data=False：不自动 add_runtime；仅签发声明句柄
        assert contract.is_loaded is False

    def test_issue_unknown_key_raises(self):
        with pytest.raises(ValueError, match="未发现"):
            ContractIssuer.issue("nonexistent.key.zzz", fill_in_data=False)

    def test_issue_fill_in_data_uses_loader(self):
        key = DATA_KEY.STOCK_LIST
        prev_discovered = ContractIssuer._discovered
        prev_cache = dict(ContractIssuer._declarations_cache)
        try:
            ContractIssuer._discovered = True
            ContractIssuer._declarations_cache = {
                key: {"meta": {"key": key, "type": "non_time_series", "scope": "global"}}
            }
            mock_contract = Mock(spec=BaseDataContract)
            with patch.object(
                ContractIssuer,
                "_create_contract_from_declaration_static",
                return_value=mock_contract,
            ):
                result = ContractIssuer.issue(key, fill_in_data=True)
            mock_contract.fill_in_data.assert_called_once()
            assert result is mock_contract
        finally:
            ContractIssuer._discovered = prev_discovered
            ContractIssuer._declarations_cache = prev_cache

    def test_system_registry_source_path(self):
        path = ContractIssuer.system_registry_source_path()
        assert path is not None
        assert path.name == "data_keys.py"
        assert path.is_file()
