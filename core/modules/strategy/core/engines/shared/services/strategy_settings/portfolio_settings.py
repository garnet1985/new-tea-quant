"""``settings.portfolio`` — 资金模拟与 allocation 配置。

本文件:
- AllocationConfig / OutputConfig / PortfolioSettings
  边界: 负责 portfolio section；不负责 EnterSelection 或 PortfolioSimulator 回放
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .settings_base import SettingsBase
from .validation_report import ValidationReport

_VALID_MODES = frozenset({"equal_capital", "equal_shares", "kelly", "custom"})


@dataclass
class AllocationConfig:
    """``settings.portfolio.allocation``。"""

    mode: str = "equal_capital"
    max_portfolio_size: int = 10
    max_weight_per_stock: float = 0.3
    lots_per_trade: int = 1
    kelly_fraction: float = 0.5
    skip_trade_when_insufficient: bool = False


@dataclass
class OutputConfig:
    """``settings.portfolio.output``。"""

    save_trades: bool = True
    save_equity_curve: bool = True


@dataclass
class PortfolioSettings(SettingsBase):
    """``settings.portfolio`` 资金模拟配置。"""

    raw_settings: Dict[str, Any]

    @property
    def portfolio(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "portfolio")

    def apply_defaults(self) -> None:
        block = self.raw_settings.setdefault("portfolio", {})
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["portfolio"] = block
        block.setdefault("initial_capital", 1_000_000)
        alloc = block.get("allocation")
        if not isinstance(alloc, dict):
            alloc = {}
            block["allocation"] = alloc
        alloc.setdefault("mode", "equal_capital")
        alloc.setdefault("max_portfolio_size", 10)
        alloc.setdefault("max_weight_per_stock", 0.3)
        alloc.setdefault("lots_per_trade", 1)
        alloc.setdefault("kelly_fraction", 0.5)
        alloc.setdefault("skip_trade_when_insufficient", False)
        out = block.get("output")
        if not isinstance(out, dict):
            out = {}
            block["output"] = out
        out.setdefault("save_trades", True)
        out.setdefault("save_equity_curve", True)

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if "portfolio" in self.raw_settings and not isinstance(
            self.raw_settings.get("portfolio"), dict
        ):
            SettingsBase.add_critical(
                report,
                "portfolio",
                "portfolio must be dict",
                suggested_fix="Set portfolio to {} or omit",
            )
            return report
        if "capital_simulator" in self.raw_settings:
            SettingsBase.add_critical(
                report,
                "capital_simulator",
                "capital_simulator renamed to portfolio",
                suggested_fix='Rename settings key "capital_simulator" → "portfolio"',
            )

        self.apply_defaults()
        block = self.raw_settings.setdefault("portfolio", {})
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["portfolio"] = block
        try:
            ic = float(block.get("initial_capital", 1_000_000))
        except (TypeError, ValueError):
            ic = 0.0
        block["initial_capital"] = max(ic, 0.0)
        if block["initial_capital"] < 1000:
            SettingsBase.add_critical(
                report,
                "portfolio.initial_capital",
                "initial_capital 必须 >= 1000",
            )

        alloc = self.allocation
        if alloc.mode not in _VALID_MODES:
            SettingsBase.add_critical(
                report,
                "portfolio.allocation.mode",
                f"allocation.mode 无效: {alloc.mode}",
            )
        if alloc.max_portfolio_size <= 0:
            SettingsBase.add_critical(
                report,
                "portfolio.allocation.max_portfolio_size",
                "max_portfolio_size 必须 > 0",
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        return SettingsBase.deep_copy_dict(dict(self.portfolio))

    @property
    def initial_capital(self) -> float:
        try:
            return float(self.portfolio.get("initial_capital", 1_000_000))
        except (TypeError, ValueError):
            return 1_000_000.0

    @property
    def allocation(self) -> AllocationConfig:
        return self._parse_allocation()

    @property
    def output(self) -> OutputConfig:
        return self._parse_output()

    def fees_config(self) -> Dict[str, Any]:
        """根级 ``settings.fees``（FeesSettings 仍为空壳时的读取入口）。"""
        top = self.raw_settings.get("fees", {}) or {}
        return top if isinstance(top, dict) else {}

    def _parse_allocation(self) -> AllocationConfig:
        a = self.portfolio.get("allocation") or {}
        if not isinstance(a, dict):
            a = {}
        return AllocationConfig(
            mode=str(a.get("mode", "equal_capital") or "equal_capital"),
            max_portfolio_size=self._as_int(a.get("max_portfolio_size"), 10, minimum=1),
            max_weight_per_stock=self._as_float_clamped(
                a.get("max_weight_per_stock"), 0.3, lo=0.0, hi=1.0
            ),
            lots_per_trade=self._as_int(a.get("lots_per_trade"), 1, minimum=1),
            kelly_fraction=self._as_float_clamped(
                a.get("kelly_fraction"), 0.5, lo=0.0, hi=1.0
            ),
            skip_trade_when_insufficient=bool(
                a.get("skip_trade_when_insufficient", False)
            ),
        )

    def _parse_output(self) -> OutputConfig:
        o = self.portfolio.get("output") or {}
        if not isinstance(o, dict):
            o = {}
        return OutputConfig(
            save_trades=bool(o.get("save_trades", True)),
            save_equity_curve=bool(o.get("save_equity_curve", True)),
        )

    @staticmethod
    def _as_int(value: Any, default: int, *, minimum: Optional[int] = None) -> int:
        try:
            n = int(value)
        except (TypeError, ValueError):
            n = default
        if minimum is not None:
            n = max(n, minimum)
        return n

    @staticmethod
    def _as_float_clamped(
        value: Any,
        default: float,
        *,
        lo: float,
        hi: float,
    ) -> float:
        try:
            x = float(value)
        except (TypeError, ValueError):
            x = default
        return max(min(x, hi), lo)


__all__ = [
    "AllocationConfig",
    "OutputConfig",
    "PortfolioSettings",
]
