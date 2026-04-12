#!/usr/bin/env python3
"""
枚举器设置

职责：
- 解析枚举器特定配置
- 验证枚举器必要字段
- 提供枚举器配置访问
"""

from dataclasses import dataclass
from typing import Dict, Any, Literal, Optional
from .base_settings import BaseSettings
from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult
from .goal_validator import GoalValidator
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnumeratorSettings(BaseSettings):
    """
    枚举器设置
    
    配置字段：
    - use_sampling: 是否使用采样配置（默认 False）
    - max_test_versions: 最多保留的测试版本数（默认 10）
    - max_output_versions: 最多保留的输出版本数（默认 3）
    - max_workers: 最大进程数（默认 "auto"）
    """
    
    # 枚举器特定字段（延迟提取）
    _use_sampling: Optional[bool] = None
    _max_test_versions: Optional[int] = None
    _max_output_versions: Optional[int] = None
    _max_workers: Optional[Literal["auto"] | int] = None
    
    # 验证状态
    _enumerator_validated: bool = False
    
    def validate_and_prepare(self) -> SettingValidationResult:
        """
        验证并准备枚举器设置
        
        验证内容：
        - goal 配置必须存在（Critical，除非 customized）
        - 添加默认值
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 提取字段并添加默认值
        self._extract_enumerator_fields()
        
        # 验证 goal 配置（Critical）
        goal_config = self.get_goal_config()
        goal_result = GoalValidator.validate_goal_config(
            goal_config, self.strategy_name, "goal"
        )
        result.errors.extend(goal_result.errors)
        result.warnings.extend(goal_result.warnings)
        if not goal_result.is_valid:
            result.is_valid = False
        
        # use_sampling 警告（如果未配置）
        if self._use_sampling is None:
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path="enumerator.use_sampling",
                message="use_sampling 未配置，默认使用 False（全量枚举，结果保存在 output/ 目录）",
                suggested_fix='在 settings.py 的 enumerator 中添加 "use_sampling": True 以启用采样枚举'
            ))
        
        # 记录警告
        result.log_warnings(logger)
        
        # 标记已验证
        self._enumerator_validated = True
        
        return result
    
    def _extract_enumerator_fields(self) -> None:
        """提取枚举器特定字段并添加默认值"""
        enumerator_config = self.raw_settings.get("enumerator", {})
        
        # use_sampling（默认 False）
        use_sampling = enumerator_config.get("use_sampling")
        if use_sampling is None:
            self._use_sampling = False  # 枚举器默认 False
        else:
            self._use_sampling = bool(use_sampling)
        
        # max_test_versions（默认 10）
        max_test = enumerator_config.get("max_test_versions", 10)
        try:
            self._max_test_versions = max(int(max_test), 1)
        except (TypeError, ValueError):
            self._max_test_versions = 10
        
        # max_output_versions（默认 3）
        max_output = enumerator_config.get("max_output_versions", 3)
        try:
            self._max_output_versions = max(int(max_output), 1)
        except (TypeError, ValueError):
            self._max_output_versions = 3
        
        # max_workers（默认 "auto"）
        max_workers = enumerator_config.get("max_workers", "auto")
        if max_workers == "auto" or max_workers is None:
            self._max_workers = "auto"
        else:
            try:
                self._max_workers = max(int(max_workers), 1)
            except (TypeError, ValueError):
                self._max_workers = "auto"
    
    @property
    def use_sampling(self) -> bool:
        """是否使用采样配置"""
        if self._use_sampling is None:
            self._extract_enumerator_fields()
        return self._use_sampling
    
    @property
    def max_test_versions(self) -> int:
        """最多保留的测试版本数"""
        if self._max_test_versions is None:
            self._extract_enumerator_fields()
        return self._max_test_versions
    
    @property
    def max_output_versions(self) -> int:
        """最多保留的输出版本数"""
        if self._max_output_versions is None:
            self._extract_enumerator_fields()
        return self._max_output_versions
    
    @property
    def max_workers(self) -> Literal["auto"] | int:
        """最大进程数"""
        if self._max_workers is None:
            self._extract_enumerator_fields()
        return self._max_workers
    
    @classmethod
    def from_base_settings(cls, base_settings: BaseSettings) -> 'EnumeratorSettings':
        """
        从基础设置创建枚举器设置
        
        Args:
            base_settings: 基础设置实例
        
        Returns:
            EnumeratorSettings 实例（未验证）
        """
        return cls(raw_settings=base_settings.raw_settings)
