#!/usr/bin/env python3
"""
扫描器设置

职责：
- 解析扫描器特定配置
- 提供配置访问
"""

from dataclasses import dataclass
from typing import Dict, Any, Literal, Optional, List
from .base_settings import BaseSettings
from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScannerSettings(BaseSettings):
    """
    扫描器设置
    
    配置字段：
    - max_workers: 最大进程数（默认 "auto"）
    - adapters: 适配器名称列表（默认 ["console"]），支持多个
    - use_strict_previous_trading_day: 是否严格按上一个交易日扫描（默认 True）
    - max_cache_days: 最多缓存多少个交易日的结果（默认 10）
    """
    
    # 扫描器特定字段（延迟提取）
    _max_workers: Optional[Literal["auto"] | int] = None
    _adapter_names: Optional[List[str]] = None  # 支持多个 adapter
    _use_strict_previous_trading_day: Optional[bool] = None
    _max_cache_days: Optional[int] = None
    
    # 验证状态
    _scanner_validated: bool = False
    
    def validate_and_prepare(self) -> SettingValidationResult:
        """
        验证并准备扫描器设置
        
        验证内容：
        - 无 Critical 错误（所有字段都有默认值）
        - 验证 adapter 是否可用（Warning 级别）
        - 添加默认值
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 提取字段并添加默认值
        self._extract_scanner_fields()
        
        # 验证 adapter（Warning 级别）
        self._validate_adapters(result)
        
        # 扫描器设置没有 Critical 错误（所有字段都有默认值）
        
        # 标记已验证
        self._scanner_validated = True
        
        return result
    
    def _validate_adapters(self, result: SettingValidationResult) -> None:
        """验证 adapter 是否可用（Warning 级别）"""
        from app.core.modules.adapter import validate_adapter
        
        adapter_names = self.adapter_names
        
        # 如果没有配置 adapter，不验证（会使用默认输出）
        if not adapter_names:
            return
        
        for adapter_name in adapter_names:
            is_valid, error_message = validate_adapter(adapter_name)
            if not is_valid:
                result.errors.append(SettingError(
                    level=SettingErrorLevel.WARNING,
                    field_path=f"scanner.adapters[{adapter_name}]",
                    message=f"适配器 '{adapter_name}' 不可用: {error_message}",
                    suggested_fix=(
                        f"请检查 userspace/adapters/{adapter_name}/adapter.py 是否存在，"
                        f"或从 scanner.adapters 中移除 '{adapter_name}'"
                    )
                ))
    
    def _extract_scanner_fields(self) -> None:
        """提取扫描器特定字段并添加默认值"""
        scanner_config = self.raw_settings.get("scanner", {})
        
        # max_workers（默认 "auto"）
        max_workers = scanner_config.get("max_workers", "auto")
        if max_workers == "auto" or max_workers is None:
            self._max_workers = "auto"
        else:
            try:
                self._max_workers = max(int(max_workers), 1)
            except (TypeError, ValueError):
                self._max_workers = "auto"
        
        # adapter_names（支持多个，默认 ["console"]）
        adapter_config = scanner_config.get("adapters", [])
        if isinstance(adapter_config, str):
            # 兼容旧配置：单个字符串
            self._adapter_names = [adapter_config] if adapter_config else ["console"]
        elif isinstance(adapter_config, list):
            # 新配置：列表
            self._adapter_names = adapter_config if adapter_config else ["console"]
        else:
            # 兼容旧配置：adapter_name
            adapter_name = scanner_config.get("adapter_name", "console")
            self._adapter_names = [adapter_name] if adapter_name else ["console"]
        
        # use_strict_previous_trading_day（默认 True）
        self._use_strict_previous_trading_day = scanner_config.get(
            "use_strict_previous_trading_day", 
            True
        )
        if not isinstance(self._use_strict_previous_trading_day, bool):
            self._use_strict_previous_trading_day = True
        
        # max_cache_days（默认 10）
        max_cache_days = scanner_config.get("max_cache_days", 10)
        try:
            self._max_cache_days = max(int(max_cache_days), 1)
        except (TypeError, ValueError):
            self._max_cache_days = 10
    
    @property
    def max_workers(self) -> Literal["auto"] | int:
        """最大进程数"""
        if self._max_workers is None:
            self._extract_scanner_fields()
        return self._max_workers
    
    @property
    def adapter_names(self) -> List[str]:
        """适配器名称列表"""
        if self._adapter_names is None:
            self._extract_scanner_fields()
        return self._adapter_names
    
    @property
    def use_strict_previous_trading_day(self) -> bool:
        """是否严格按上一个交易日扫描"""
        if self._use_strict_previous_trading_day is None:
            self._extract_scanner_fields()
        return self._use_strict_previous_trading_day
    
    @property
    def max_cache_days(self) -> int:
        """最多缓存多少个交易日的结果"""
        if self._max_cache_days is None:
            self._extract_scanner_fields()
        return self._max_cache_days
    
    @classmethod
    def from_base_settings(cls, base_settings: BaseSettings) -> 'ScannerSettings':
        """
        从基础设置创建扫描器设置
        
        Args:
            base_settings: 基础设置实例
        
        Returns:
            ScannerSettings 实例（未验证）
        """
        return cls(raw_settings=base_settings.raw_settings)
