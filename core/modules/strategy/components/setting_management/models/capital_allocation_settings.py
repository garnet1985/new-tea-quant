#!/usr/bin/env python3
"""
资金分配模拟器设置

职责：
- 解析资金分配模拟器特定配置
- 验证必要字段
- 提供配置访问
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Literal, Optional
from .base_settings import BaseSettings
from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult
import logging

logger = logging.getLogger(__name__)


@dataclass
class AllocationConfig:
    """资金分配配置"""
    mode: Literal["equal_capital", "equal_shares", "kelly", "custom"] = "equal_capital"
    max_portfolio_size: int = 5
    max_weight_per_stock: float = 0.3
    lot_size: int = 100
    lots_per_trade: int = 1
    kelly_fraction: float = 0.5


@dataclass
class OutputConfig:
    """输出配置"""
    save_trades: bool = True
    save_equity_curve: bool = True


@dataclass
class CapitalAllocationSettings(BaseSettings):
    """
    资金分配模拟器设置
    
    配置字段：
    - sot_version: SOT 版本依赖（默认 "latest"）
    - use_sampling: 是否使用采样配置（默认 True）
    - initial_capital: 初始资金（默认 1_000_000，最小值 1000）
    - allocation: 资金分配配置
    - output: 输出配置
    """
    
    # 资金分配模拟器特定字段（延迟提取）
    _sot_version: Optional[str] = None
    _use_sampling: Optional[bool] = None
    _initial_capital: Optional[float] = None
    _allocation: Optional[AllocationConfig] = None
    _output: Optional[OutputConfig] = None
    
    # 验证状态
    _capital_allocation_validated: bool = False
    
    def validate_and_prepare(self) -> SettingValidationResult:
        """
        验证并准备资金分配模拟器设置
        
        验证内容：
        - initial_capital 必须 >= 1000（Critical）
        - allocation.mode 必须是有效枚举值（Critical）
        - allocation.max_portfolio_size 必须 > 0（Critical）
        - 添加默认值
        - 检查 sot_version（Warning）
        - 检查 fees 配置（Warning）
        
        Returns:
            SettingValidationResult: 验证结果
        """
        result = SettingValidationResult(is_valid=True)
        
        # 提取字段并添加默认值
        self._extract_capital_allocation_fields()
        
        # 验证 initial_capital（Critical）
        if self._initial_capital < 1000:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="capital_simulator.initial_capital",
                message=f"initial_capital ({self._initial_capital}) 必须 >= 1000 元，否则无法购买任何股票",
                suggested_fix='在 settings.py 的 capital_simulator 中将 "initial_capital" 设置为至少 1000'
            ))
            result.is_valid = False
        
        # 验证 allocation.mode（Critical）
        valid_modes = ["equal_capital", "equal_shares", "kelly", "custom"]
        if self._allocation.mode not in valid_modes:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="capital_simulator.allocation.mode",
                message=f"allocation.mode ({self._allocation.mode}) 必须是以下值之一: {valid_modes}",
                suggested_fix=f'在 settings.py 的 capital_simulator.allocation 中将 "mode" 设置为 {valid_modes} 之一'
            ))
            result.is_valid = False
        
        # 验证 allocation.max_portfolio_size（Critical）
        if self._allocation.max_portfolio_size <= 0:
            result.errors.append(SettingError(
                level=SettingErrorLevel.CRITICAL,
                field_path="capital_simulator.allocation.max_portfolio_size",
                message=f"max_portfolio_size ({self._allocation.max_portfolio_size}) 必须 > 0",
                suggested_fix='在 settings.py 的 capital_simulator.allocation 中将 "max_portfolio_size" 设置为大于 0 的整数'
            ))
            result.is_valid = False
        
        # 检查 sot_version（Warning）
        if self._sot_version and self._sot_version != "latest":
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path="capital_simulator.sot_version",
                message=f"指定的 SOT 版本 '{self._sot_version}' 将在运行时检查，如果不存在将使用 'latest'",
                suggested_fix="如果版本不存在，系统将自动使用 'latest'，如果 'latest' 也不存在，建议先运行枚举器"
            ))
        
        # 检查 fees 配置（Warning）
        fees_config = self.get_fees_config_with_priority()
        if not fees_config or all(
            fees_config.get(key, 0.0) == 0.0
            for key in ["commission_rate", "stamp_duty_rate", "transfer_fee_rate"]
        ):
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path="fees",
                message="fees 配置缺失或所有费率为 0，将忽略交易费用",
                suggested_fix=(
                    '在 settings.py 中添加 fees 配置，例如：\n'
                    '  "fees": {\n'
                    '    "commission_rate": 0.00025,\n'
                    '    "min_commission": 5.0,\n'
                    '    "stamp_duty_rate": 0.001,\n'
                    '    "transfer_fee_rate": 0.0\n'
                    '  }'
                )
            ))
        
        # use_sampling 警告（如果未配置）
        if self._use_sampling is None:
            result.warnings.append(SettingError(
                level=SettingErrorLevel.WARNING,
                field_path="capital_simulator.use_sampling",
                message="use_sampling 未配置，默认使用 True（在枚举器采样结果中抽样）",
                suggested_fix='在 settings.py 的 capital_simulator 中添加 "use_sampling": False 以使用全量结果'
            ))
        
        # 记录警告
        result.log_warnings(logger)
        
        # 标记已验证
        self._capital_allocation_validated = True
        
        return result
    
    def _extract_capital_allocation_fields(self) -> None:
        """提取资金分配模拟器特定字段并添加默认值"""
        capital_config = self.raw_settings.get("capital_simulator", {})
        
        # sot_version（默认 "latest"）
        self._sot_version = capital_config.get("sot_version", "latest") or "latest"
        
        # use_sampling（默认 True）
        use_sampling = capital_config.get("use_sampling")
        if use_sampling is None:
            self._use_sampling = True  # 模拟器默认 True
        else:
            self._use_sampling = bool(use_sampling)
        
        # initial_capital（默认 1_000_000）
        initial_capital = capital_config.get("initial_capital", 1_000_000)
        try:
            self._initial_capital = max(float(initial_capital), 0.0)
        except (TypeError, ValueError):
            self._initial_capital = 1_000_000.0
        
        # allocation
        allocation_config = capital_config.get("allocation", {}) or {}
        self._allocation = AllocationConfig(
            mode=allocation_config.get("mode", "equal_capital"),
            max_portfolio_size=max(int(allocation_config.get("max_portfolio_size", 5)), 1),
            max_weight_per_stock=max(min(float(allocation_config.get("max_weight_per_stock", 0.3)), 1.0), 0.0),
            lot_size=max(int(allocation_config.get("lot_size", 100)), 1),
            lots_per_trade=max(int(allocation_config.get("lots_per_trade", 1)), 1),
            kelly_fraction=max(min(float(allocation_config.get("kelly_fraction", 0.5)), 1.0), 0.0),
        )
        
        # output
        output_config = capital_config.get("output", {}) or {}
        self._output = OutputConfig(
            save_trades=bool(output_config.get("save_trades", True)),
            save_equity_curve=bool(output_config.get("save_equity_curve", True)),
        )
    
    @property
    def sot_version(self) -> str:
        """SOT 版本依赖"""
        if self._sot_version is None:
            self._extract_capital_allocation_fields()
        return self._sot_version
    
    @property
    def use_sampling(self) -> bool:
        """是否使用采样配置"""
        if self._use_sampling is None:
            self._extract_capital_allocation_fields()
        return self._use_sampling
    
    @property
    def initial_capital(self) -> float:
        """初始资金"""
        if self._initial_capital is None:
            self._extract_capital_allocation_fields()
        return self._initial_capital
    
    @property
    def allocation(self) -> AllocationConfig:
        """资金分配配置"""
        if self._allocation is None:
            self._extract_capital_allocation_fields()
        return self._allocation
    
    @property
    def output(self) -> OutputConfig:
        """输出配置"""
        if self._output is None:
            self._extract_capital_allocation_fields()
        return self._output
    
    def get_fees_config_with_priority(self) -> Dict[str, Any]:
        """
        获取交易成本配置（带优先级）
        
        优先级：capital_simulator.fees > simulator.fees > top_level.fees
        
        Returns:
            fees 配置字典
        """
        capital_config = self.raw_settings.get("capital_simulator", {})
        simulator_config = self.raw_settings.get("simulator", {})
        top_level_fees = self.get_fees_config()
        
        # 按优先级返回
        return (
            capital_config.get("fees") or
            simulator_config.get("fees") or
            top_level_fees or
            {}
        )
    
    @classmethod
    def from_base_settings(cls, base_settings: BaseSettings) -> 'CapitalAllocationSettings':
        """
        从基础设置创建资金分配模拟器设置
        
        Args:
            base_settings: 基础设置实例
        
        Returns:
            CapitalAllocationSettings 实例（未验证）
        """
        return cls(raw_settings=base_settings.raw_settings)
