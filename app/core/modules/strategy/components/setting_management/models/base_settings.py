#!/usr/bin/env python3
"""
设置基类

职责：
- 加载原始 settings 字典（不验证）
- 提供按需验证方法
- 提供公共字段访问
- 添加默认值
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import importlib
import logging

from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult

logger = logging.getLogger(__name__)


@dataclass
class BaseSettings(ABC):
    """
    设置基类
    
    职责：
    - 加载原始 settings 字典（不验证）
    - 提供按需验证方法
    - 提供公共字段访问
    - 添加默认值
    """
    
    # 原始配置字典（保留完整原始数据）
    raw_settings: Dict[str, Any]
    
    # 策略基本信息（延迟提取）
    _strategy_name: Optional[str] = None
    _strategy_description: Optional[str] = None
    _is_enabled: Optional[bool] = None
    
    # 验证状态
    _base_validated: bool = False
    
    def __post_init__(self):
        """初始化后不立即验证，只提取基本信息"""
        self._extract_basic_info()
    
    def _extract_basic_info(self) -> None:
        """提取策略基本信息（不验证）"""
        self._strategy_name = self.raw_settings.get("name", "unknown")
        self._strategy_description = self.raw_settings.get("description", "")
        self._is_enabled = bool(self.raw_settings.get("is_enabled", False))
    
    @property
    def strategy_name(self) -> str:
        """获取策略名称"""
        if self._strategy_name is None:
            self._extract_basic_info()
        return self._strategy_name or "unknown"
    
    @property
    def strategy_description(self) -> str:
        """获取策略描述"""
        if self._strategy_description is None:
            self._extract_basic_info()
        return self._strategy_description or ""
    
    @property
    def is_enabled(self) -> bool:
        """是否启用"""
        if self._is_enabled is None:
            self._extract_basic_info()
        return self._is_enabled
    
    # =========================================================================
    # 验证方法（按需调用）
    # =========================================================================
    
    def validate_base_settings(self) -> SettingValidationResult:
        """
        验证基础设置（Critical）
        
        验证内容：
        - name 不能为空或 'unknown'（Critical）
        - data.base_price_source 不能为空（Critical）
        - data.adjust_type 不能为空（Critical）
        
        同时添加默认值：
        - data.min_required_records: 默认 100
        - data.indicators: 默认 {}
        - data.extra_data_sources: 默认 []
        - sampling.strategy: 默认 "continuous"
        - sampling.sampling_amount: 默认 10
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 验证 name
        if not self.strategy_name or self.strategy_name == "unknown":
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="name",
                message="策略名称不能为空或 'unknown'",
                suggested_fix='在 settings.py 中添加 "name": "your_strategy_name"'
            ))
            result.is_valid = False
        
        # 验证 data.base_price_source
        data_config = self.raw_settings.get("data", {})
        base_price_source = data_config.get("base_price_source")
        if not base_price_source:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="data.base_price_source",
                message="基础价格数据源不能为空",
                suggested_fix='在 settings.py 的 data 中添加 "base_price_source": "stock_kline_daily"'
            ))
            result.is_valid = False
        
        # 验证 data.adjust_type
        adjust_type = data_config.get("adjust_type")
        if not adjust_type:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="data.adjust_type",
                message="复权类型不能为空",
                suggested_fix='在 settings.py 的 data 中添加 "adjust_type": "qfq"'
            ))
            result.is_valid = False
        
        # 添加默认值（不验证，直接添加）
        self._add_base_default_values()
        
        # 标记已验证
        self._base_validated = True
        
        return result
    
    def _add_base_default_values(self) -> None:
        """添加基础设置的默认值"""
        # 确保 data 存在
        if "data" not in self.raw_settings:
            self.raw_settings["data"] = {}
        
        data_config = self.raw_settings["data"]
        
        # min_required_records 默认值
        if "min_required_records" not in data_config:
            data_config["min_required_records"] = 100
        elif not isinstance(data_config["min_required_records"], int) or data_config["min_required_records"] <= 0:
            data_config["min_required_records"] = 100
        
        # indicators 默认值
        if "indicators" not in data_config:
            data_config["indicators"] = {}
        
        # extra_data_sources 默认值
        if "extra_data_sources" not in data_config:
            data_config["extra_data_sources"] = []
        elif not isinstance(data_config["extra_data_sources"], list):
            data_config["extra_data_sources"] = []
        
        # sampling 默认值
        if "sampling" not in self.raw_settings:
            self.raw_settings["sampling"] = {}
        
        sampling_config = self.raw_settings["sampling"]
        if "strategy" not in sampling_config:
            sampling_config["strategy"] = "continuous"
        if "sampling_amount" not in sampling_config:
            sampling_config["sampling_amount"] = 10
    
    # =========================================================================
    # 公共字段访问（所有组件都需要）
    # =========================================================================
    
    def get_core_config(self) -> Dict[str, Any]:
        """获取核心配置（策略特定参数）"""
        return self.raw_settings.get("core", {})
    
    def get_data_config(self) -> Dict[str, Any]:
        """获取数据配置"""
        return self.raw_settings.get("data", {})
    
    def get_sampling_config(self) -> Dict[str, Any]:
        """获取采样配置"""
        return self.raw_settings.get("sampling", {})
    
    def get_goal_config(self) -> Dict[str, Any]:
        """获取投资目标配置（止盈止损）"""
        # 优先从顶层 goal 读取，如果没有则从 simulator.goal 读取
        goal = self.raw_settings.get("goal")
        if goal:
            return goal
        simulator = self.raw_settings.get("simulator", {})
        return simulator.get("goal", {})
    
    def get_fees_config(self) -> Dict[str, Any]:
        """获取交易成本配置"""
        return self.raw_settings.get("fees", {})
    
    # =========================================================================
    # 数据配置便捷访问
    # =========================================================================
    
    def get_base_price_source(self) -> str:
        """获取基础价格数据源"""
        data_config = self.get_data_config()
        return data_config.get("base_price_source", "stock_kline_daily")
    
    def get_adjust_type(self) -> str:
        """获取复权类型"""
        data_config = self.get_data_config()
        return data_config.get("adjust_type", "qfq")
    
    def get_min_required_records(self) -> int:
        """获取最小要求记录数"""
        data_config = self.get_data_config()
        min_records = data_config.get("min_required_records", 100)
        try:
            return max(int(min_records), 1)
        except (TypeError, ValueError):
            return 100
    
    def get_indicators_config(self) -> Dict[str, Any]:
        """获取技术指标配置"""
        data_config = self.get_data_config()
        return data_config.get("indicators", {})
    
    def get_extra_data_sources(self) -> list:
        """获取额外数据源列表"""
        data_config = self.get_data_config()
        extra_sources = data_config.get("extra_data_sources", [])
        return extra_sources if isinstance(extra_sources, list) else []
    
    # =========================================================================
    # 采样配置便捷访问
    # =========================================================================
    
    def get_sampling_strategy(self) -> str:
        """获取采样策略"""
        sampling_config = self.get_sampling_config()
        return sampling_config.get("strategy", "continuous")
    
    def get_sampling_amount(self) -> int:
        """获取采样数量"""
        sampling_config = self.get_sampling_config()
        amount = sampling_config.get("sampling_amount", 10)
        try:
            return max(int(amount), 1)
        except (TypeError, ValueError):
            return 10
    
    # =========================================================================
    # 工具方法
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（返回原始配置，包含已添加的默认值）"""
        return self.raw_settings
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（直接访问原始配置）"""
        return self.raw_settings.get(key, default)
    
    @classmethod
    def load_from_strategy_name(cls, strategy_name: str) -> 'BaseSettings':
        """
        从策略名称加载设置（不验证）
        
        Args:
            strategy_name: 策略名称（对应 userspace/strategies/{strategy_name}）
        
        Returns:
            BaseSettings 实例（未验证）
        
        Raises:
            ValueError: 如果加载失败
        """
        settings_module_path = f"app.userspace.strategies.{strategy_name}.settings"
        
        try:
            settings_module = importlib.import_module(settings_module_path)
        except ModuleNotFoundError as e:
            raise ValueError(
                f"[BaseSettings] 无法加载策略 settings: {settings_module_path}"
            ) from e
        
        raw_settings = getattr(settings_module, "settings", None)
        if not isinstance(raw_settings, dict):
            raise ValueError(
                f"[BaseSettings] 策略 {strategy_name} 的 settings.py 中缺少 'settings' 字典"
            )
        
        return cls(raw_settings=raw_settings)
