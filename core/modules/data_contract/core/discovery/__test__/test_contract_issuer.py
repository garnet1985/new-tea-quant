"""ContractIssuer discovery / get_contract / register（实现测）。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.force_run

from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import (
    BaseDataContract,
    BaseTimeSeriesContract,
    ContractType,
    ContractScope,
)
from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader


class TestContractIssuerDiscovery:
    """测试 ContractIssuer 的发现功能。"""

    def test_discover_system_contracts(self):
        """测试 discover()：发现系统 contract。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 验证发现的 contract 不为空
        keys = issuer.list_available_keys()
        assert len(keys) > 0

        # 验证发现了一些已知的系统 contract
        assert "stock.kline.daily" in keys
        assert "stock.list" in keys
        assert "trade.calendar" in keys

    def test_discover_with_user_space_path(self):
        """测试 discover()：发现系统 + 用户 contract。"""
        issuer = ContractIssuer()
        # 使用不存在的用户空间路径（不会报错）
        issuer.discover(user_space_path=Path("/tmp/nonexistent"))

        # 仍然能发现系统 contract
        keys = issuer.list_available_keys()
        assert len(keys) > 0

    def test_list_available_keys(self):
        """测试 list_available_keys()：列出所有 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        keys = issuer.list_available_keys()

        # 验证返回类型
        assert isinstance(keys, list)
        assert all(isinstance(key, str) for key in keys)

        # 验证包含已知 key
        assert "stock.kline.daily" in keys

    def test_list_system_keys(self):
        """测试 list_system_keys()：列出系统 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        system_keys = issuer.list_system_keys()

        # 验证返回类型
        assert isinstance(system_keys, list)
        assert all(isinstance(key, str) for key in system_keys)

        # 验证包含已知系统 key
        assert "stock.kline.daily" in system_keys
        assert "stock.list" in system_keys

    def test_list_user_keys(self):
        """测试 list_user_keys()：列出用户 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        user_keys = issuer.list_user_keys()

        # 验证返回类型
        assert isinstance(user_keys, list)
        # 默认情况下，用户 key 为空（没有用户自定义 contract）
        assert len(user_keys) == 0

    def test_is_customized_for_system_key(self):
        """测试 is_customized()：检查系统 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 系统 key 应该返回 False
        assert issuer.is_customized("stock.kline.daily") is False
        assert issuer.is_customized("stock.list") is False

    def test_is_customized_for_nonexistent_key(self):
        """测试 is_customized()：检查不存在的 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 不存在的 key 应该抛出 KeyError
        with pytest.raises(KeyError, match="不存在"):
            issuer.is_customized("nonexistent.key")

    def test_is_available(self):
        """测试 is_available()：检查 key 是否可用。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 存在的 key 应该返回 True
        assert issuer.is_available("stock.kline.daily") is True
        assert issuer.is_available("stock.list") is True

        # 不存在的 key 应该返回 False
        assert issuer.is_available("nonexistent.key") is False

    def test_get_validation_errors(self):
        """测试 get_validation_errors()：获取验证错误。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 获取验证错误
        errors = issuer.get_validation_errors()

        # 验证返回类型
        assert isinstance(errors, dict)


class TestContractIssuerGetContract:
    """测试 ContractIssuer 的获取 contract 功能。"""

    def test_get_contract_time_series(self):
        """测试 get_contract()：获取时间序列 contract。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 验证返回类型
        assert isinstance(contract, BaseDataContract)
        assert isinstance(contract, BaseTimeSeriesContract)

        # 验证 meta 信息
        assert contract.meta.key == "stock.kline.daily"
        assert contract.meta.type == ContractType.TIME_SERIES
        assert contract.meta.scope == ContractScope.PER_ENTITY

    def test_get_contract_non_time_series(self):
        """测试 get_contract()：获取非时间序列 contract。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.list")

        # 验证返回类型
        assert isinstance(contract, BaseDataContract)
        # stock.list 不是时间序列
        assert contract.meta.type == ContractType.NON_TIME_SERIES
        assert contract.meta.scope == ContractScope.GLOBAL

    def test_get_contract_global_scope(self):
        """测试 get_contract()：获取 global scope contract。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("trade.calendar")

        # 验证 scope
        assert contract.meta.scope == ContractScope.GLOBAL

    def test_get_contract_per_entity_scope(self):
        """测试 get_contract()：获取 per_entity scope contract。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 验证 scope
        assert contract.meta.scope == ContractScope.PER_ENTITY

    def test_get_contract_nonexistent_key(self):
        """测试 get_contract()：获取不存在的 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 不存在的 key 应该抛出 KeyError
        with pytest.raises(KeyError, match="不存在"):
            issuer.get_contract("nonexistent.key")


class TestContractIssuerRegisterCustomDeclaration:
    """测试 ContractIssuer 的自定义声明注册功能。"""

    def test_register_custom_declaration_success(self):
        """测试 register_custom_declaration()：成功注册自定义声明。"""
        issuer = ContractIssuer()

        # 创建自定义 declaration
        custom_declaration = {
            "meta": {
                "key": "custom.test",
                "type": "time_series",
                "scope": "global",
                "loader": Mock(spec=BaseDataContractLoader),
            }
        }

        # 注册自定义 declaration
        issuer.register_custom_declaration(custom_declaration)

        # 验证注册成功
        assert issuer.is_available("custom.test") is True
        assert issuer.is_customized("custom.test") is True

        # 验证出现在用户 key 列表中
        user_keys = issuer.list_user_keys()
        assert "custom.test" in user_keys

    def test_register_custom_declaration_duplicate_key(self):
        """测试 register_custom_declaration()：重复 key 应该失败。"""
        issuer = ContractIssuer()

        # 创建自定义 declaration
        custom_declaration = {
            "meta": {
                "key": "custom.test",
                "type": "time_series",
                "scope": "global",
                "loader": Mock(spec=BaseDataContractLoader),
            }
        }

        # 注册两次
        issuer.register_custom_declaration(custom_declaration)

        # 第二次注册应该失败
        with pytest.raises(ValueError, match="已存在"):
            issuer.register_custom_declaration(custom_declaration)

    def test_register_custom_declaration_missing_key(self):
        """测试 register_custom_declaration()：缺少 key 应该失败。"""
        issuer = ContractIssuer()

        # 创建缺少 key 的 declaration
        invalid_declaration = {
            "meta": {
                "type": "time_series",
                "scope": "global",
            }
        }

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="缺少.*key"):
            issuer.register_custom_declaration(invalid_declaration)

    def test_register_custom_declaration_invalid_type(self):
        """测试 register_custom_declaration()：无效的 type 应该失败。"""
        issuer = ContractIssuer()

        # 创建无效 type 的 declaration
        invalid_declaration = {
            "meta": {
                "key": "custom.test",
                "type": "invalid_type",
                "scope": "global",
            }
        }

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="验证失败"):
            issuer.register_custom_declaration(invalid_declaration)

