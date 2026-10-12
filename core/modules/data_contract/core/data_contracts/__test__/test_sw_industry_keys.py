"""申万行业和货币供应量数据键能被发现。"""
from __future__ import annotations

from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import SYS_DATA_KEY


def test_sw_and_money_supply_keys_are_registered():
    issuer = ContractIssuer()
    issuer.discover()
    keys = issuer.list_available_keys()
    assert SYS_DATA_KEY.SW_INDUSTRY in keys
    assert SYS_DATA_KEY.SW_INDUSTRY_LIST in keys
    assert SYS_DATA_KEY.STOCK_SW_INDUSTRY in keys
    assert SYS_DATA_KEY.SW_INDUSTRY_KLINE_DAILY in keys
    assert SYS_DATA_KEY.MACRO_MONEY_SUPPLY in keys
    assert "stock.industry" not in keys
    assert issuer.get_validation_errors() == {}


def test_sw_list_data_keys():
    assert ContractIssuer.get_list_data_key("stock.sw_industry") == "stock.list"
    assert ContractIssuer.get_list_data_key("sw.industry.kline.daily") == "sw.industry.list"
