"""新实现 API 的契约测试（ContractIssuer, BaseDataContract, BaseTimeSeriesContract）。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    sys.modules["pandas"] = types.ModuleType("pandas")

from core.modules.data_contract.contracts import (
    ContractIssuer,
    BaseDataContract,
    BaseTimeSeriesContract,
    ContractType,
    ContractScope,
    ContractMeta,
    ContractRuntime,
)
from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader


# ============================================================================
# ContractIssuer API 测试
# ============================================================================

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

        # 正常情况下应该没有错误（或只有少量错误）
        # 注意：这个测试依赖于实际的 contract 声明


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


# ============================================================================
# BaseDataContract API 测试
# ============================================================================

class TestBaseDataContractBasics:
    """测试 BaseDataContract 的基础功能。"""

    def test_contract_initialization(self):
        """测试 contract 初始化。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 验证 contract_id 存在且唯一
        assert contract.contract_id is not None
        assert "stock.kline.daily" in contract.contract_id

        # 验证 meta 信息
        assert contract.meta.key == "stock.kline.daily"
        assert contract.meta.display_name == "股票日K线"

    def test_contract_meta_properties(self):
        """测试 contract meta 属性。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 验证 meta 属性
        assert contract.meta.key == "stock.kline.daily"
        assert contract.meta.type == ContractType.TIME_SERIES
        assert contract.meta.scope == ContractScope.PER_ENTITY
        assert contract.meta.loader is not None

    def test_contract_runtime_initialization(self):
        """测试 contract runtime 初始化。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 验证 runtime 初始状态（空）
        assert contract.runtime.start_time is None
        assert contract.runtime.end_time is None
        assert contract.runtime.entity_ids is None

    def test_add_runtime(self):
        """测试 add_runtime()：添加 runtime。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 添加 runtime
        runtime = {
            "start_time": "20200101",
            "end_time": "20201231",
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        }

        result = contract.add_runtime(runtime)

        # 验证链式调用
        assert result is contract

        # 验证 runtime 信息
        assert contract.runtime.start_time == "20200101"
        assert contract.runtime.end_time == "20201231"
        assert contract.runtime.entity_ids == ["600000.SH"]

        # 验证动态字段
        assert hasattr(contract.runtime, "adjust")
        assert contract.runtime.adjust == "qfq"

    def test_is_global(self):
        """测试 is_global()：检查 scope。"""
        issuer = ContractIssuer()
        issuer.discover()

        # Global scope
        global_contract = issuer.get_contract("stock.list")
        assert global_contract.is_global() is True

        # Per entity scope
        per_entity_contract = issuer.get_contract("stock.kline.daily")
        assert per_entity_contract.is_global() is False

    def test_is_time_series(self):
        """测试 is_time_series()：检查 type。"""
        issuer = ContractIssuer()
        issuer.discover()

        # Time series
        time_series_contract = issuer.get_contract("stock.kline.daily")
        assert time_series_contract.is_time_series() is True

        # Non time series
        non_time_series_contract = issuer.get_contract("stock.list")
        assert non_time_series_contract.is_time_series() is False

    def test_runtime_fingerprint(self):
        """测试 runtime_fingerprint：缓存标识。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 初始状态：fingerprint 为 None
        assert contract.runtime_fingerprint is None

        # 添加 runtime
        contract.add_runtime({
            "start_time": "20200101",
            "end_time": "20201231",
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })

        # 验证 fingerprint 已更新
        fingerprint = contract._calculate_runtime_fingerprint()
        assert fingerprint is not None
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA256 hex string

        # 相同的 runtime 应该产生相同的 fingerprint
        fingerprint2 = contract._calculate_runtime_fingerprint()
        assert fingerprint == fingerprint2

        # 不同的 runtime 应该产生不同的 fingerprint
        contract.add_runtime({
            "start_time": "20210101",
            "end_time": "20211231",
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })
        fingerprint3 = contract._calculate_runtime_fingerprint()
        assert fingerprint3 != fingerprint

    def test_contract_id_uniqueness(self):
        """测试 contract_id：唯一标识。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 创建两个相同 key 的 contract
        contract1 = issuer.get_contract("stock.kline.daily")
        contract2 = issuer.get_contract("stock.kline.daily")

        # 验证 contract_id 不同
        assert contract1.contract_id != contract2.contract_id


class TestBaseDataContractFillInData:
    """测试 BaseDataContract 的数据加载功能。"""

    def test_fill_in_data_global_scope(self):
        """测试 fill_in_data()：加载 global scope 数据。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.list")

        # Mock loader class and instance
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{"symbol": "600000.SH", "name": "浦发银行"}]
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        # 加载数据
        contract.fill_in_data()

        # 验证 loader 被调用
        mock_loader_instance.load.assert_called_once()

        # 验证数据已加载
        assert contract.data is not None
        assert contract.is_loaded is True

    def test_fill_in_data_per_entity_single(self):
        """测试 fill_in_data()：加载单个 entity 数据。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader class and instance
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{"date": "20200101", "close": 10.0}]
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        # 添加 runtime（单个 entity）
        contract.add_runtime({
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })

        # 加载数据
        contract.fill_in_data()

        # 验证 loader 被调用（单个 entity 应该调用 load）
        mock_loader_instance.load.assert_called_once()

        # 验证参数包含 entity_id
        call_args = mock_loader_instance.load.call_args[0][0]
        assert call_args["entity_id"] == "600000.SH"

        # 验证数据已加载
        assert contract.data is not None
        assert contract.is_loaded is True

    def test_fill_in_data_per_entity_multiple(self):
        """测试 fill_in_data()：加载多个 entity 数据。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader class and instance
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load_batch.return_value = {
            "600000.SH": [{"date": "20200101", "close": 10.0}],
            "600001.SH": [{"date": "20200101", "close": 20.0}],
        }
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        # 添加 runtime（多个 entity）
        entity_ids = ["600000.SH", "600001.SH"]
        contract.add_runtime({
            "entity_ids": entity_ids,
            "adjust": "qfq",
        })

        # 加载数据
        contract.fill_in_data()

        # 验证 loader 被调用（多个 entity 应该调用 load_batch）
        mock_loader_instance.load_batch.assert_called_once()

        # 验证参数
        call_args = mock_loader_instance.load_batch.call_args
        assert call_args[0][0] == entity_ids  # 第一个位置参数
        assert call_args[0][1]["adjust"] == "qfq"  # 第二个位置参数

        # 验证数据已加载
        assert contract.data is not None
        assert "600000.SH" in contract.data
        assert "600001.SH" in contract.data

    def test_fill_in_data_with_runtime_parameter(self):
        """测试 fill_in_data()：通过参数传递 runtime。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader class and instance
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{"date": "20200101", "close": 10.0}]
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        # 通过参数传递 runtime
        contract.fill_in_data(runtime={
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })

        # 验证 loader 被调用
        mock_loader_instance.load.assert_called_once()

        # 验证数据已加载
        assert contract.data is not None

    def test_fill_in_data_caching(self):
        """测试 fill_in_data()：缓存机制。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader class and instance
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{"date": "20200101", "close": 10.0}]
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        # 第一次加载
        contract.fill_in_data(runtime={
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })

        assert mock_loader_instance.load.call_count == 1

        # 第二次加载（相同 runtime，应该使用缓存）
        contract.fill_in_data()

        # loader 不应该被再次调用
        assert mock_loader_instance.load.call_count == 1

    def test_fill_in_data_force_reload(self):
        """测试 fill_in_data()：强制重新加载。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader class and instance
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{"date": "20200101", "close": 10.0}]
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        # 第一次加载
        contract.fill_in_data(runtime={
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })

        assert mock_loader_instance.load.call_count == 1

        # 强制重新加载
        contract.fill_in_data(force_reload=True)

        # loader 应该被再次调用
        assert mock_loader_instance.load.call_count == 2

    def test_fill_in_data_missing_runtime_per_entity(self):
        """测试 fill_in_data()：缺少 runtime 参数（per_entity）。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader
        mock_loader = Mock(spec=BaseDataContractLoader)
        contract.meta.loader = mock_loader

        # 尝试加载（per_entity 需要 entity_ids）
        with pytest.raises(ValueError, match="需要 runtime.entity_ids"):
            contract.fill_in_data()

    def test_fill_in_data_missing_loader(self):
        """测试 fill_in_data()：缺少 loader。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 移除 loader
        contract.meta.loader = None

        # 尝试加载
        with pytest.raises(ValueError, match="没有定义 loader"):
            contract.fill_in_data(runtime={"entity_ids": ["600000.SH"]})


# ============================================================================
# BaseTimeSeriesContract API 测试
# ============================================================================

class TestBaseTimeSeriesContract:
    """测试 BaseTimeSeriesContract 的时间序列功能。"""

    def test_get_time_window(self):
        """测试 get_time_window()：获取时间窗口。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 未设置时间窗口
        window = contract.get_time_window()
        assert window is None

        # 设置时间窗口
        contract.add_runtime({
            "start_time": "20200101",
            "end_time": "20201231",
            "entity_ids": ["600000.SH"],
        })

        window = contract.get_time_window()
        assert window is not None
        assert window.start == "20200101"
        assert window.end == "20201231"

    def test_normalize_as_of_standard_format(self):
        """测试 normalize_as_of()：标准化标准格式。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # YYYYMMDD 格式
        result = contract.normalize_as_of("20200101")
        assert result == "20200101"

        # YYYY-MM-DD 格式
        result = contract.normalize_as_of("2020-01-01")
        assert result == "20200101"

    def test_normalize_as_of_quarter_format(self):
        """测试 normalize_as_of()：标准化季度格式。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 季度格式（转换为季度第一天）
        result = contract.normalize_as_of("2020Q1")
        assert result == "20200101"

        result = contract.normalize_as_of("2020Q4")
        assert result == "20201001"

    def test_get_base_time_field(self):
        """测试 get_base_time_field()：获取时间轴字段名。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 默认为 None（未指定）
        field = contract.get_base_time_field()
        assert field is None

        # 设置 runtime.base_time_field
        contract.add_runtime({
            "base_time_field": "date",
            "entity_ids": ["600000.SH"],
        })

        field = contract.get_base_time_field()
        assert field == "date"

    def test_get_time_format(self):
        """测试 get_time_format()：获取时间格式。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 默认为 None（未指定）
        time_format = contract.get_time_format()
        assert time_format is None

        # 设置 runtime.time_format
        contract.add_runtime({
            "time_format": "YYYYMMDD",
            "entity_ids": ["600000.SH"],
        })

        time_format = contract.get_time_format()
        assert time_format == "YYYYMMDD"


# ============================================================================
# 错误处理测试
# ============================================================================

class TestErrorHandling:
    """测试错误处理场景。"""

    def test_get_contract_nonexistent_key(self):
        """测试错误处理：不存在的 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 不存在的 key 应该抛出 KeyError
        with pytest.raises(KeyError, match="不存在"):
            issuer.get_contract("nonexistent.key")

    def test_missing_meta_field(self):
        """测试错误处理：缺少必要字段。"""
        issuer = ContractIssuer()

        # 创建缺少 meta 的 declaration
        invalid_declaration = {}

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="缺少.*meta"):
            BaseDataContract(invalid_declaration)

    def test_missing_meta_key(self):
        """测试错误处理：缺少 meta.key。"""
        issuer = ContractIssuer()

        # 创建缺少 meta.key 的 declaration
        invalid_declaration = {
            "meta": {
                "type": "time_series",
                "scope": "global",
            }
        }

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="缺少.*key"):
            BaseDataContract(invalid_declaration)

    def test_invalid_meta_type(self):
        """测试错误处理：无效的 meta.type。"""
        issuer = ContractIssuer()

        # 创建无效 type 的 declaration
        invalid_declaration = {
            "meta": {
                "key": "test.key",
                "type": "invalid_type",
                "scope": "global",
            }
        }

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="meta.type"):
            BaseDataContract(invalid_declaration)

    def test_invalid_meta_scope(self):
        """测试错误处理：无效的 meta.scope。"""
        issuer = ContractIssuer()

        # 创建无效 scope 的 declaration
        invalid_declaration = {
            "meta": {
                "key": "test.key",
                "type": "time_series",
                "scope": "invalid_scope",
            }
        }

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="meta.scope"):
            BaseDataContract(invalid_declaration)

    def test_invalid_runtime_missing_entity_ids(self):
        """测试错误处理：per_entity 缺少 entity_ids。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader
        mock_loader = Mock(spec=BaseDataContractLoader)
        contract.meta.loader = mock_loader

        # 尝试加载（缺少 entity_ids）
        with pytest.raises(ValueError, match="需要 runtime.entity_ids"):
            contract.fill_in_data()

    def test_register_invalid_declaration(self):
        """测试错误处理：注册无效的 declaration。"""
        issuer = ContractIssuer()

        # 创建无效的 declaration（缺少 type）
        invalid_declaration = {
            "meta": {
                "key": "test.key",
                "scope": "global",
            }
        }

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="验证失败"):
            issuer.register_custom_declaration(invalid_declaration)


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases:
    """测试边界条件。"""

    def test_multiple_discover_calls(self):
        """测试多次调用 discover()。"""
        issuer = ContractIssuer()

        # 第一次 discover
        issuer.discover()
        keys1 = issuer.list_available_keys()

        # 第二次 discover
        issuer.discover()
        keys2 = issuer.list_available_keys()

        # 应该得到相同的结果
        assert keys1 == keys2

    def test_get_declaration(self):
        """测试 get_declaration()：获取 declaration 字典。"""
        issuer = ContractIssuer()
        issuer.discover()

        declaration = issuer.get_declaration("stock.kline.daily")

        # 验证返回类型
        assert isinstance(declaration, dict)
        assert "meta" in declaration
        assert declaration["meta"]["key"] == "stock.kline.daily"

    def test_get_declaration_nonexistent_key(self):
        """测试 get_declaration()：获取不存在的 key。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 不存在的 key 应该抛出 KeyError
        with pytest.raises(KeyError, match="不存在"):
            issuer.get_declaration("nonexistent.key")

    def test_contract_with_empty_specific(self):
        """测试 contract 的 specific 为空。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # specific 默认为空实例
        assert contract.specific is not None

    def test_add_runtime_with_extra_fields(self):
        """测试 add_runtime()：包含额外字段。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # 添加包含额外字段的 runtime
        contract.add_runtime({
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
            "custom_field": "custom_value",
        })

        # 验证基础字段
        assert contract.runtime.entity_ids == ["600000.SH"]

        # 验证额外字段
        assert hasattr(contract.runtime, "adjust")
        assert contract.runtime.adjust == "qfq"
        assert hasattr(contract.runtime, "custom_field")
        assert contract.runtime.custom_field == "custom_value"

    def test_get_entity_data_global_scope(self):
        """测试 get_entity_data()：global scope。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.list")

        # Mock 数据
        contract.data = [{"symbol": "600000.SH", "name": "浦发银行"}]

        # Global scope 应该返回相同数据
        data = contract.get_entity_data("any_entity_id")
        assert data == contract.data

    def test_get_entity_data_per_entity_scope(self):
        """测试 get_entity_data()：per_entity scope。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock 数据（per_entity 格式）
        contract.data = {
            "600000.SH": [{"date": "20200101", "close": 10.0}],
            "600001.SH": [{"date": "20200101", "close": 20.0}],
        }

        # 获取特定 entity 数据
        data = contract.get_entity_data("600000.SH")
        assert data == [{"date": "20200101", "close": 10.0}]

        # 获取不存在的 entity
        data = contract.get_entity_data("nonexistent.SH")
        assert data is None

    def test_get_entities_data_global_scope(self):
        """测试 get_entities_data()：global scope。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.list")

        # Mock 数据和 runtime
        contract.data = [{"symbol": "600000.SH", "name": "浦发银行"}]
        contract.runtime.entity_ids = ["600000.SH", "600001.SH"]

        # Global scope 应该返回所有 entity 映射到相同数据
        entities_data = contract.get_entities_data()
        assert entities_data is not None
        assert len(entities_data) == 2
        assert entities_data["600000.SH"] == contract.data
        assert entities_data["600001.SH"] == contract.data

    def test_get_entities_data_per_entity_scope(self):
        """测试 get_entities_data()：per_entity scope。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock 数据
        contract.data = {
            "600000.SH": [{"date": "20200101", "close": 10.0}],
            "600001.SH": [{"date": "20200101", "close": 20.0}],
        }

        # 获取所有 entities 数据
        entities_data = contract.get_entities_data()
        assert entities_data is not None
        assert len(entities_data) == 2
        assert "600000.SH" in entities_data
        assert "600001.SH" in entities_data


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """测试集成场景。"""

    def test_full_workflow_time_series(self):
        """测试完整工作流：时间序列 contract。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 1. 获取 contract
        contract = issuer.get_contract("stock.kline.daily")

        # 2. 验证 meta
        assert contract.meta.key == "stock.kline.daily"
        assert contract.is_time_series() is True
        assert contract.is_global() is False

        # 3. 添加 runtime
        contract.add_runtime({
            "start_time": "20200101",
            "end_time": "20201231",
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })

        # 4. 验证 runtime
        assert contract.runtime.start_time == "20200101"
        assert contract.runtime.end_time == "20201231"
        assert hasattr(contract.runtime, "adjust")
        assert contract.runtime.adjust == "qfq"

        # 5. 获取时间窗口
        window = contract.get_time_window()
        assert window is not None
        assert window.start == "20200101"
        assert window.end == "20201231"

        # 6. 标准化时间
        normalized = contract.normalize_as_of("2020-01-01")
        assert normalized == "20200101"

    def test_full_workflow_non_time_series(self):
        """测试完整工作流：非时间序列 contract。"""
        issuer = ContractIssuer()
        issuer.discover()

        # 1. 获取 contract
        contract = issuer.get_contract("stock.list")

        # 2. 验证 meta
        assert contract.meta.key == "stock.list"
        assert contract.is_time_series() is False
        assert contract.is_global() is True

        # 3. 加载数据（global scope 不需要 runtime）
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{"symbol": "600000.SH", "name": "浦发银行"}]
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        contract.fill_in_data()

        # 4. 验证数据
        assert contract.data is not None
        assert contract.is_loaded is True

    def test_runtime_fingerprint_change_detection(self):
        """测试 runtime fingerprint 变化检测。"""
        issuer = ContractIssuer()
        issuer.discover()

        contract = issuer.get_contract("stock.kline.daily")

        # Mock loader class and instance
        mock_loader_class = Mock(spec=BaseDataContractLoader)
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [{"date": "20200101", "close": 10.0}]
        mock_loader_class.return_value = mock_loader_instance
        contract.meta.loader = mock_loader_class

        # 第一次加载
        contract.fill_in_data(runtime={
            "entity_ids": ["600000.SH"],
            "adjust": "qfq",
        })

        assert mock_loader_instance.load.call_count == 1

        # 更改 runtime
        contract.add_runtime({
            "entity_ids": ["600000.SH"],
            "adjust": "hfq",  # 不同的复权方式
        })

        # 再次加载（runtime 已更新，应该重新加载）
        contract.fill_in_data()

        # loader 应该被再次调用
        assert mock_loader_instance.load.call_count == 2