#!/usr/bin/env python3
"""
CapitalAllocationSimulator 配置模型

负责从 StrategySettings 中解析 CapitalAllocationSimulator 所需配置
"""

from dataclasses import dataclass
from typing import Dict, Any, Literal


@dataclass
class CapitalAllocationSimulatorConfig:
    """
    CapitalAllocationSimulator 的基础配置

    这些配置从 userspace 策略的 settings 中派生。
    """

    # SOT 版本号；"latest" 表示使用最新的 SOT 版本目录
    # 支持格式：
    #   - "latest": 使用最新的 SOT 版本
    #   - "1_20260112_161317": 使用指定版本号
    #   - "test/latest": 使用最新的测试版本（test/ 目录）
    #   - "sot/latest": 使用最新的 SOT 版本（sot/ 目录，默认）
    sot_version: str = "latest"

    # 是否使用采样配置（默认 True，使用 sampling 配置过滤股票）
    use_sampling: bool = True

    # 初始资金（元）
    initial_capital: float = 1_000_000.0

    # 资金分配模式
    allocation_mode: Literal["equal_capital", "equal_shares", "kelly"] = "equal_capital"

    # 最大组合持仓数（同时最多持有多少只股票）
    max_portfolio_size: int = 10

    # 单只股票最大权重（0~1，防止过度集中）
    # 例如：总资产100万，某只股票最多占30万（30%），超过时需要减仓
    max_weight_per_stock: float = 0.3

    # equal_shares 模式下的配置
    lot_size: int = 100              # 1手对应的股票数（A股通常是100股）
    lots_per_trade: int = 1          # 每次买入的手数（例如：1手、2手等）

    # kelly 模式下的配置
    kelly_fraction: float = 0.5       # Kelly 仓位的折扣比例（0~1，用于风险控制）

    # 交易成本（从顶层 fees 或 capital_simulator.fees 读取）
    commission_rate: float = 0.00025
    min_commission: float = 5.0
    stamp_duty_rate: float = 0.001
    transfer_fee_rate: float = 0.0

    # 输出控制
    save_trades: bool = True          # 是否保存逐笔交易日志
    save_equity_curve: bool = True    # 是否保存每日权益曲线

    @classmethod
    def from_settings(cls, settings) -> "CapitalAllocationSimulatorConfig":
        """
        从 StrategySettings 中提取 CapitalAllocationSimulator 所需配置

        配置优先级：
        - fees: capital_simulator.fees > simulator.fees > 顶层 fees > 默认值
        - 其他字段：capital_simulator.* > 默认值
        """
        settings_dict = settings.to_dict()
        capital_sim_cfg = settings_dict.get("capital_simulator", {}) or {}
        simulator_cfg = settings_dict.get("simulator", {}) or {}
        top_level_fees = settings_dict.get("fees", {}) or {}

        # SOT 版本号（枚举版本依赖）
        sot_version = capital_sim_cfg.get("sot_version", "latest")

        # 是否使用采样（默认 True）
        use_sampling = capital_sim_cfg.get("use_sampling", True)
        if not isinstance(use_sampling, bool):
            use_sampling = True  # 如果不是 bool，默认 True

        # 初始资金
        initial_capital = float(capital_sim_cfg.get("initial_capital", 1_000_000) or 1_000_000)

        # 资金分配配置
        allocation_cfg = capital_sim_cfg.get("allocation", {}) or {}
        allocation_mode = allocation_cfg.get("mode", "equal_capital")
        max_portfolio_size = int(allocation_cfg.get("max_portfolio_size", 10) or 10)
        max_weight_per_stock = float(allocation_cfg.get("max_weight_per_stock", 0.3) or 0.3)
        lot_size = int(allocation_cfg.get("lot_size", 100) or 100)
        lots_per_trade = int(allocation_cfg.get("lots_per_trade", 1) or 1)
        kelly_fraction = float(allocation_cfg.get("kelly_fraction", 0.5) or 0.5)

        # 交易成本（优先级：capital_simulator.fees > simulator.fees > 顶层 fees > 默认值）
        fees_cfg = capital_sim_cfg.get("fees") or simulator_cfg.get("fees") or top_level_fees or {}
        commission_rate = float(fees_cfg.get("commission_rate", 0.00025) or 0.00025)
        min_commission = float(fees_cfg.get("min_commission", 5.0) or 5.0)
        stamp_duty_rate = float(fees_cfg.get("stamp_duty_rate", 0.001) or 0.001)
        transfer_fee_rate = float(fees_cfg.get("transfer_fee_rate", 0.0) or 0.0)

        # 输出控制
        output_cfg = capital_sim_cfg.get("output", {}) or {}
        save_trades = output_cfg.get("save_trades", True)
        if not isinstance(save_trades, bool):
            save_trades = True
        save_equity_curve = output_cfg.get("save_equity_curve", True)
        if not isinstance(save_equity_curve, bool):
            save_equity_curve = True

        return cls(
            sot_version=sot_version,
            use_sampling=use_sampling,
            initial_capital=initial_capital,
            allocation_mode=allocation_mode,
            max_portfolio_size=max_portfolio_size,
            max_weight_per_stock=max_weight_per_stock,
            lot_size=lot_size,
            lots_per_trade=lots_per_trade,
            kelly_fraction=kelly_fraction,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_duty_rate=stamp_duty_rate,
            transfer_fee_rate=transfer_fee_rate,
            save_trades=save_trades,
            save_equity_curve=save_equity_curve,
        )

