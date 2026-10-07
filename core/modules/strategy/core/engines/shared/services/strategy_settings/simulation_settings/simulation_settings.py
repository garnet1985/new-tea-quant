"""``settings.simulation`` 门面（execution / assumption / risk_control / price）。

本文件:
- SimulationSettings: 子 section 聚合与 enter/exit 价解析 API
  边界: 负责 simulation 配置对象化；不负责 Investment 反应式推进或 price 回放
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

from .assumption import AssumptionSettings
from .execution import BacktestPeriod, ExecutionSettings
from .price import PriceReplaySettings
from .risk_control import RiskControl
from .tradability import EdgesConfig, LiquidityConfig, TradabilityConfig

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.investment import (
        TargetCheckStep,
    )


@dataclass
class SimulationSettings(SettingsBase):
    """``settings.simulation`` — 组合 execution / assumption / risk_control / price。"""

    raw_settings: Dict[str, Any]
    execution: ExecutionSettings = field(init=False, repr=False)
    assumption: AssumptionSettings = field(init=False, repr=False)
    risk_control: RiskControl = field(init=False, repr=False)
    price: PriceReplaySettings = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "execution", ExecutionSettings(raw_settings=self.raw_settings)
        )
        object.__setattr__(
            self, "assumption", AssumptionSettings(raw_settings=self.raw_settings)
        )
        object.__setattr__(
            self, "risk_control", RiskControl(raw_settings=self.raw_settings)
        )
        object.__setattr__(
            self, "price", PriceReplaySettings(raw_settings=self.raw_settings)
        )

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def start_date(self) -> str:
        return self.execution.start_date

    @property
    def end_date(self) -> str:
        return self.execution.end_date

    @property
    def mode(self) -> str:
        return self.execution.mode

    @property
    def target_check_order(self) -> List[str]:
        return self.assumption.target_check_order

    @property
    def tradability(self) -> TradabilityConfig:
        return self.assumption.tradability

    @property
    def edges(self) -> EdgesConfig:
        return self.tradability.edges

    @property
    def liquidity(self) -> LiquidityConfig:
        return self.tradability.liquidity

    @property
    def enter_price(self) -> str:
        return self.tradability.enter_price

    @property
    def exit_price(self) -> str:
        return self.tradability.exit_price

    @property
    def monitor_price(self) -> str:
        return self.tradability.monitor_price

    @property
    def delisted_exit_price(self) -> str:
        return self.tradability.delisted_exit_price

    @property
    def allow_enter_at_limit_up(self) -> bool:
        return self.edges.allow_enter_at_limit_up

    @property
    def allow_exit_at_limit_down(self) -> bool:
        return self.edges.allow_exit_at_limit_down

    def parsed_target_check_order(self) -> List["TargetCheckStep"]:
        return self.assumption.parsed_target_check_order()

    def resolve_period(self) -> BacktestPeriod:
        """回测前：补齐空 start/end 后的开市日区间。"""
        return self.execution.resolve_period()

    def apply_defaults(self) -> None:
        if "simulation" not in self.raw_settings or not isinstance(
            self.raw_settings["simulation"], dict
        ):
            self.raw_settings["simulation"] = {}
        self.execution.apply_defaults()
        self.assumption.apply_defaults()
        self.risk_control.apply_defaults()
        self.price.apply_defaults()

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if not isinstance(self.raw_settings.get("simulation"), dict):
            SettingsBase.add_critical(
                report,
                "simulation",
                "simulation must be dict",
                suggested_fix="Set simulation to {}",
            )
            return report

        for part in (self.execution, self.assumption, self.risk_control, self.price):
            part_report = part.validate()
            report.errors.extend(part_report.errors)
            report.warnings.extend(part_report.warnings)
            if not part_report.is_valid:
                report.is_valid = False

        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "execution": self.execution.to_dict(),
            "assumption": self.assumption.to_dict(),
            "risk_control": self.risk_control.to_dict(),
            "price": self.price.to_dict(),
        }


__all__ = ["SimulationSettings"]
