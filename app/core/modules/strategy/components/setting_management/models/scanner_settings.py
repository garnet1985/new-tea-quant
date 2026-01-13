#!/usr/bin/env python3
"""
扫描器设置

职责：
- 解析扫描器特定配置
- 提供配置访问
"""

from dataclasses import dataclass
from typing import Dict, Any, Literal, Optional
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
    - adapter_name: 适配器名称（默认 "console"）
    """
    
    # 扫描器特定字段（延迟提取）
    _max_workers: Optional[Literal["auto"] | int] = None
    _adapter_name: Optional[str] = None
    
    # 验证状态
    _scanner_validated: bool = False
    
    def validate_and_prepare(self) -> SettingValidationResult:
        """
        验证并准备扫描器设置
        
        验证内容：
        - 无 Critical 错误（所有字段都有默认值）
        - 添加默认值
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 提取字段并添加默认值
        self._extract_scanner_fields()
        
        # 扫描器设置没有 Critical 错误（所有字段都有默认值）
        
        # 标记已验证
        self._scanner_validated = True
        
        return result
    
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
        
        # adapter_name（默认 "console"）
        self._adapter_name = scanner_config.get("adapter_name", "console") or "console"
    
    @property
    def max_workers(self) -> Literal["auto"] | int:
        """最大进程数"""
        if self._max_workers is None:
            self._extract_scanner_fields()
        return self._max_workers
    
    @property
    def adapter_name(self) -> str:
        """适配器名称"""
        if self._adapter_name is None:
            self._extract_scanner_fields()
        return self._adapter_name
    
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
