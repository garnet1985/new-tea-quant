#!/usr/bin/env python3
"""
策略设置（主设置类）

职责：
- 继承 BaseSettings
- 提供完整的策略配置访问
- 作为所有子 Settings 的工厂入口
"""

from dataclasses import dataclass
from typing import Dict, Any
from .base_settings import BaseSettings
from .setting_errors import SettingValidationResult


@dataclass
class StrategySettings(BaseSettings):
    """
    策略设置（主设置类）
    
    职责：
    - 继承 BaseSettings
    - 提供完整的策略配置访问
    - 作为所有子 Settings 的工厂入口
    """
    
    def validate_and_prepare(self) -> SettingValidationResult:
        """
        验证并准备设置（第一步，必须调用）
        
        验证基础设置（Critical），添加默认值
        
        Returns:
            SettingValidationResult: 验证结果
        
        Raises:
            ValueError: 如果有 Critical 错误
        """
        result = self.validate_base_settings()
        result.raise_if_critical()  # 如果有 Critical 错误，抛出异常
        return result
    
    # =========================================================================
    # 组件配置访问（用于创建子 Settings）
    # =========================================================================
    
    def get_enumerator_config(self) -> Dict[str, Any]:
        """获取枚举器配置"""
        return self.raw_settings.get("enumerator", {})
    
    def get_price_factor_config(self) -> Dict[str, Any]:
        """获取价格因子模拟器配置（兼容旧名称 simulator）"""
        return self.raw_settings.get("simulator", {})
    
    def get_capital_allocation_config(self) -> Dict[str, Any]:
        """获取资金分配模拟器配置"""
        return self.raw_settings.get("capital_simulator", {})
    
    def get_scanner_config(self) -> Dict[str, Any]:
        """获取扫描器配置"""
        return self.raw_settings.get("scanner", {})
    
    # =========================================================================
    # 工厂方法（创建子 Settings，自动验证）
    # =========================================================================
    
    def create_enumerator_settings(self) -> 'EnumeratorSettings':
        """
        创建枚举器设置（自动验证）
        
        Returns:
            EnumeratorSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        from .enumerator_settings import EnumeratorSettings
        
        # 确保基础设置已验证
        if not self._base_validated:
            self.validate_and_prepare()
        
        enumerator_settings = EnumeratorSettings.from_base_settings(self)
        result = enumerator_settings.validate_and_prepare()
        result.raise_if_critical()
        
        return enumerator_settings
    
    def create_price_factor_settings(self) -> 'PriceFactorSettings':
        """
        创建价格因子模拟器设置（自动验证）
        
        Returns:
            PriceFactorSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        from .price_factor_settings import PriceFactorSettings
        
        # 确保基础设置已验证
        if not self._base_validated:
            self.validate_and_prepare()
        
        price_factor_settings = PriceFactorSettings.from_base_settings(self)
        result = price_factor_settings.validate_and_prepare()
        result.raise_if_critical()
        
        return price_factor_settings
    
    def create_capital_allocation_settings(self) -> 'CapitalAllocationSettings':
        """
        创建资金分配模拟器设置（自动验证）
        
        Returns:
            CapitalAllocationSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        from .capital_allocation_settings import CapitalAllocationSettings
        
        # 确保基础设置已验证
        if not self._base_validated:
            self.validate_and_prepare()
        
        capital_allocation_settings = CapitalAllocationSettings.from_base_settings(self)
        result = capital_allocation_settings.validate_and_prepare()
        result.raise_if_critical()
        
        return capital_allocation_settings
    
    def create_scanner_settings(self) -> 'ScannerSettings':
        """
        创建扫描器设置（自动验证）
        
        Returns:
            ScannerSettings 实例（已验证）
        
        Raises:
            ValueError: 如果验证失败（Critical）
        """
        from .scanner_settings import ScannerSettings
        
        # 确保基础设置已验证
        if not self._base_validated:
            self.validate_and_prepare()
        
        scanner_settings = ScannerSettings.from_base_settings(self)
        result = scanner_settings.validate_and_prepare()
        result.raise_if_critical()
        
        return scanner_settings
