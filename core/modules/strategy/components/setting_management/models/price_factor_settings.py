#!/usr/bin/env python3
"""
价格因子模拟器设置

职责：
- 解析价格因子模拟器特定配置
- 验证必要字段
- 提供配置访问
"""

from dataclasses import dataclass
from typing import Dict, Any, Literal, Optional
from .base_settings import BaseSettings
from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult
import logging

logger = logging.getLogger(__name__)


@dataclass
class PriceFactorSettings(BaseSettings):
    """
    价格因子模拟器设置
    
    配置字段：
    - sot_version: SOT 版本依赖（默认 "latest"）
    - use_sampling: 是否使用采样配置（默认 True）
    - start_date: 模拟开始日期（可选，默认从默认开始日期）
    - end_date: 模拟结束日期（可选，默认到最新交易日）
    - max_workers: 最大进程数（默认 "auto"）
    """
    
    # 价格因子模拟器特定字段（延迟提取）
    _sot_version: Optional[str] = None
    _use_sampling: Optional[bool] = None
    _start_date: Optional[str] = None
    _end_date: Optional[str] = None
    _max_workers: Optional[Literal["auto"] | int] = None
    
    # 验证状态
    _price_factor_validated: bool = False
    
    def validate_and_prepare(self) -> SettingValidationResult:
        """
        验证并准备价格因子模拟器设置
        
        验证内容：
        - 无 Critical 错误（所有字段都有默认值或可选）
        - 添加默认值
        - 检查 sot_version（Warning）
        - 检查 start_date / end_date（Warning）
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 提取字段并添加默认值
        self._extract_price_factor_fields()
        
        # 检查 sot_version（Warning）
        if self._sot_version and self._sot_version != "latest":
            # 这里只标记 Warning，实际版本检查在运行时进行
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path="simulator.sot_version",
                message=f"指定的 SOT 版本 '{self._sot_version}' 将在运行时检查，如果不存在将使用 'latest'",
                suggested_fix="如果版本不存在，系统将自动使用 'latest'，如果 'latest' 也不存在，建议先运行枚举器"
            ))
        
        # 检查 start_date / end_date（Warning）
        if not self._start_date or not self._end_date:
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path="simulator.start_date / end_date",
                message="start_date 或 end_date 未配置，将使用默认时间范围（从默认开始日期到最新交易日）",
                suggested_fix=(
                    '在 settings.py 的 simulator 中配置时间范围，例如：\n'
                    '  "simulator": {\n'
                    '    "start_date": "20240101",\n'
                    '    "end_date": "20241231"\n'
                    '  }'
                )
            ))
        
        # use_sampling 警告（如果未配置）
        if self._use_sampling is None:
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path="simulator.use_sampling",
                message="use_sampling 未配置，默认使用 True（在枚举器采样结果中抽样）",
                suggested_fix='在 settings.py 的 simulator 中添加 "use_sampling": False 以使用全量结果'
            ))
        
        # 记录警告
        result.log_warnings(logger)
        
        # 标记已验证
        self._price_factor_validated = True
        
        return result
    
    def _extract_price_factor_fields(self) -> None:
        """提取价格因子模拟器特定字段并添加默认值"""
        simulator_config = self.raw_settings.get("simulator", {})
        
        # sot_version（默认 "latest"）
        self._sot_version = simulator_config.get("sot_version", "latest") or "latest"
        
        # use_sampling（默认 True）
        use_sampling = simulator_config.get("use_sampling")
        if use_sampling is None:
            self._use_sampling = True  # 模拟器默认 True
        else:
            self._use_sampling = bool(use_sampling)
        
        # start_date / end_date（默认空字符串）
        self._start_date = simulator_config.get("start_date", "") or ""
        self._end_date = simulator_config.get("end_date", "") or ""
        
        # max_workers（默认 "auto"）
        max_workers = simulator_config.get("max_workers", "auto")
        if max_workers == "auto" or max_workers is None:
            self._max_workers = "auto"
        else:
            try:
                self._max_workers = max(int(max_workers), 1)
            except (TypeError, ValueError):
                self._max_workers = "auto"
    
    @property
    def sot_version(self) -> str:
        """SOT 版本依赖"""
        if self._sot_version is None:
            self._extract_price_factor_fields()
        return self._sot_version
    
    @property
    def use_sampling(self) -> bool:
        """是否使用采样配置"""
        if self._use_sampling is None:
            self._extract_price_factor_fields()
        return self._use_sampling
    
    @property
    def start_date(self) -> str:
        """模拟开始日期"""
        if self._start_date is None:
            self._extract_price_factor_fields()
        return self._start_date
    
    @property
    def end_date(self) -> str:
        """模拟结束日期"""
        if self._end_date is None:
            self._extract_price_factor_fields()
        return self._end_date
    
    @property
    def max_workers(self) -> Literal["auto"] | int:
        """最大进程数"""
        if self._max_workers is None:
            self._extract_price_factor_fields()
        return self._max_workers
    
    def get_default_date_range(self) -> tuple[str, str]:
        """
        获取默认日期范围（需要访问 DataManager）
        
        Returns:
            (start_date, end_date): 默认开始日期和最新交易日
        """
        from core.modules.data_manager import DataManager
        from core.utils.date.date_utils import DateUtils
        
        data_mgr = DataManager(is_verbose=False)
        
        # 获取默认开始日期（使用 DateUtils.DEFAULT_START_DATE）
        start_date = DateUtils.DEFAULT_START_DATE
        
        # 获取最新交易日
        try:
            end_date = data_mgr.service.calendar.get_latest_completed_trading_date()
        except Exception as e:
            logger.warning(f"无法获取最新交易日，使用空字符串: {e}")
            end_date = ""
        
        return start_date, end_date
    
    @classmethod
    def from_base_settings(cls, base_settings: BaseSettings) -> 'PriceFactorSettings':
        """
        从基础设置创建价格因子模拟器设置
        
        Args:
            base_settings: 基础设置实例
        
        Returns:
            PriceFactorSettings 实例（未验证）
        """
        return cls(raw_settings=base_settings.raw_settings)
