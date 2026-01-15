#!/usr/bin/env python3
"""
设置管理器

职责：
- 统一加载和验证策略设置
- 提供组件特定设置的访问接口
- 管理设置的验证状态
"""

from typing import Dict, Any, Optional
import logging

from .models import (
    StrategySettings,
    EnumeratorSettings,
    PriceFactorSettings,
    CapitalAllocationSettings,
    ScannerSettings,
    SettingValidationResult,
)

logger = logging.getLogger(__name__)


class SettingManager:
    """
    设置管理器
    
    职责：
    - 加载策略设置（第一步）
    - 验证基础设置（Critical）
    - 提供组件特定设置的访问接口
    - 管理设置的验证状态
    """
    
    def __init__(self, strategy_name: str):
        """
        初始化设置管理器
        
        Args:
            strategy_name: 策略名称
        
        Raises:
            ValueError: 如果加载失败
        """
        self.strategy_name = strategy_name
        
        # 加载策略设置（不验证）
        self.base_settings: StrategySettings = StrategySettings.load_from_strategy_name(strategy_name)
        
        # 验证状态
        self._base_validated: bool = False
        
        # 组件设置缓存（按需创建）
        self._enumerator_settings: Optional[EnumeratorSettings] = None
        self._price_factor_settings: Optional[PriceFactorSettings] = None
        self._capital_allocation_settings: Optional[CapitalAllocationSettings] = None
        self._scanner_settings: Optional[ScannerSettings] = None
    
    def validate_base_settings(self) -> SettingValidationResult:
        """
        验证基础设置（第一步，必须调用）
        
        验证内容：
        - name, data.base_price_source, data.adjust_type（Critical）
        - 添加默认值
        
        Returns:
            SettingValidationResult: 验证结果
        
        Raises:
            ValueError: 如果有 Critical 错误
        """
        result = self.base_settings.validate_and_prepare()
        result.raise_if_critical()  # 如果有 Critical 错误，抛出异常
        
        # 记录警告
        result.log_warnings(logger)
        
        self._base_validated = True
        return result
    
    def get_enumerator_settings(self) -> EnumeratorSettings:
        """
        获取枚举器设置（自动验证）
        
        Returns:
            EnumeratorSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        if self._enumerator_settings is None:
            # 确保基础设置已验证
            if not self._base_validated:
                self.validate_base_settings()
            
            # 创建并验证枚举器设置
            self._enumerator_settings = self.base_settings.create_enumerator_settings()
        
        return self._enumerator_settings
    
    def get_price_factor_settings(self) -> PriceFactorSettings:
        """
        获取价格因子模拟器设置（自动验证）
        
        Returns:
            PriceFactorSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        if self._price_factor_settings is None:
            # 确保基础设置已验证
            if not self._base_validated:
                self.validate_base_settings()
            
            # 创建并验证价格因子模拟器设置
            self._price_factor_settings = self.base_settings.create_price_factor_settings()
        
        return self._price_factor_settings
    
    def get_capital_allocation_settings(self) -> CapitalAllocationSettings:
        """
        获取资金分配模拟器设置（自动验证）
        
        Returns:
            CapitalAllocationSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        if self._capital_allocation_settings is None:
            # 确保基础设置已验证
            if not self._base_validated:
                self.validate_base_settings()
            
            # 创建并验证资金分配模拟器设置
            self._capital_allocation_settings = self.base_settings.create_capital_allocation_settings()
        
        return self._capital_allocation_settings
    
    def get_scanner_settings(self) -> ScannerSettings:
        """
        获取扫描器设置（自动验证）
        
        Returns:
            ScannerSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        if self._scanner_settings is None:
            # 确保基础设置已验证
            if not self._base_validated:
                self.validate_base_settings()
            
            # 创建并验证扫描器设置
            self._scanner_settings = self.base_settings.create_scanner_settings()
        
        return self._scanner_settings
    
    # =========================================================================
    # 便捷访问方法（访问基础设置的公共字段）
    # =========================================================================
    
    def get_core_config(self) -> Dict[str, Any]:
        """获取核心配置（策略特定参数）"""
        return self.base_settings.get_core_config()
    
    def get_data_config(self) -> Dict[str, Any]:
        """获取数据配置"""
        return self.base_settings.get_data_config()
    
    def get_sampling_config(self) -> Dict[str, Any]:
        """获取采样配置"""
        return self.base_settings.get_sampling_config()
    
    def get_goal_config(self) -> Dict[str, Any]:
        """获取投资目标配置（止盈止损）"""
        return self.base_settings.get_goal_config()
    
    def get_fees_config(self) -> Dict[str, Any]:
        """获取交易成本配置"""
        return self.base_settings.get_fees_config()
    
    def get_base_price_source(self) -> str:
        """获取基础价格数据源"""
        return self.base_settings.get_base_price_source()
    
    def get_adjust_type(self) -> str:
        """获取复权类型"""
        return self.base_settings.get_adjust_type()
    
    def get_min_required_records(self) -> int:
        """获取最小要求记录数"""
        return self.base_settings.get_min_required_records()
    
    def get_indicators_config(self) -> Dict[str, Any]:
        """获取技术指标配置"""
        return self.base_settings.get_indicators_config()
    
    def get_extra_data_sources(self) -> list:
        """获取额外数据源列表"""
        return self.base_settings.get_extra_data_sources()
    
    def get_sampling_strategy(self) -> str:
        """获取采样策略"""
        return self.base_settings.get_sampling_strategy()
    
    def get_sampling_amount(self) -> int:
        """获取采样数量"""
        return self.base_settings.get_sampling_amount()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（返回原始配置，包含已添加的默认值）"""
        return self.base_settings.to_dict()
