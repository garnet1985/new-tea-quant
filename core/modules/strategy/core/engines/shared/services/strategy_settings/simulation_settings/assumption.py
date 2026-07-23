"""``simulation.assumption`` — template + 有效 tradability。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

from .assumption_templates import AssumptionTemplate
from .tradability import TradabilityConfig


@dataclass
class AssumptionSettings(SettingsBase):
    """``settings.simulation.assumption``。

    命名 ``template`` 短路 → 预设 tradability；``none`` / ``custom`` → 显式块。
    """

    raw_settings: Dict[str, Any]

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def assumption(self) -> Dict[str, Any]:
        block = self.simulation.get("assumption")
        return block if isinstance(block, dict) else {}

    @property
    def template(self) -> str:
        try:
            return AssumptionTemplate.canonicalize(self.assumption.get("template"))
        except ValueError:
            return str(self.assumption.get("template") or "").strip().lower()

    @property
    def tradability(self) -> TradabilityConfig:
        tmpl = self.assumption.get("template")
        if AssumptionTemplate.is_named(tmpl):
            return AssumptionTemplate.tradability(str(tmpl))
        raw = self.assumption.get("tradability")
        return TradabilityConfig.from_raw(
            raw if isinstance(raw, dict) else {},
            field_path="simulation.assumption.tradability",
        )

    def apply_defaults(self) -> None:
        sim = self.raw_settings.setdefault("simulation", {})
        if not isinstance(sim, dict):
            self.raw_settings["simulation"] = {}
            sim = self.raw_settings["simulation"]
        assumption = sim.setdefault("assumption", {})
        if not isinstance(assumption, dict):
            sim["assumption"] = {}
            assumption = sim["assumption"]

        if "template" not in assumption or assumption.get("template") is None:
            assumption["template"] = AssumptionTemplate.NONE
        else:
            try:
                assumption["template"] = AssumptionTemplate.canonicalize(
                    assumption.get("template")
                )
            except ValueError:
                pass

        tmpl = assumption.get("template")
        if AssumptionTemplate.is_named(tmpl):
            assumption["tradability"] = AssumptionTemplate.tradability_dict(str(tmpl))
        else:
            tradability = assumption.setdefault("tradability", {})
            if not isinstance(tradability, dict):
                assumption["tradability"] = {}
                tradability = assumption["tradability"]
            self._ensure_tradability_defaults(tradability)

    @staticmethod
    def _ensure_tradability_defaults(tradability: Dict[str, Any]) -> None:
        tradability.setdefault("monitor_price", "close")
        tradability.setdefault("enter_price", "next_open")
        tradability.setdefault("exit_price", "close")
        slip = tradability.setdefault("slippage", {})
        if isinstance(slip, dict):
            slip.setdefault("enter_bps", 0.0)
            slip.setdefault("exit_bps", 0.0)
        edges = tradability.setdefault("edges", {})
        if isinstance(edges, dict):
            edges.setdefault("no_next_tick", "skip_trade")
            edges.setdefault("allow_enter_at_limit_up", False)
            edges.setdefault("allow_exit_at_limit_down", False)
        liq = tradability.setdefault("liquidity", {})
        if isinstance(liq, dict):
            liq.setdefault("max_participation_rate", 0.1)
            liq.setdefault("participation_on_exceed", "clip")
        tradability.setdefault("delisted_exit_price", "last_tradable_close")

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        assumption_raw = self.simulation.get("assumption")
        if assumption_raw is not None and not isinstance(assumption_raw, dict):
            SettingsBase.add_critical(
                report,
                "simulation.assumption",
                "assumption must be dict",
            )
            return report

        try:
            tmpl = AssumptionTemplate.canonicalize(self.assumption.get("template"))
        except ValueError as exc:
            SettingsBase.add_critical(
                report,
                "simulation.assumption.template",
                str(exc),
                suggested_fix=f"Named: {sorted(AssumptionTemplate.NAMED)}; "
                "or none/custom for explicit tradability",
            )
            return report

        self.apply_defaults()

        if tmpl in AssumptionTemplate.NAMED:
            try:
                _ = self.tradability
            except ValueError as exc:
                SettingsBase.add_critical(
                    report, "simulation.assumption.tradability", str(exc)
                )
            return report

        tradability_raw = self.assumption.get("tradability")
        if tradability_raw is not None and not isinstance(tradability_raw, dict):
            SettingsBase.add_critical(
                report,
                "simulation.assumption.tradability",
                "tradability must be dict",
            )
            return report
        try:
            _ = TradabilityConfig.from_raw(
                tradability_raw if isinstance(tradability_raw, dict) else {},
                field_path="simulation.assumption.tradability",
            )
        except ValueError as exc:
            msg = str(exc)
            path = (
                "simulation.assumption.tradability.edges"
                if "edges" in msg
                else "simulation.assumption.tradability"
            )
            SettingsBase.add_critical(report, path, msg)
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "template": self.template or AssumptionTemplate.NONE,
            "tradability": self.tradability.to_dict(),
        }


__all__ = ["AssumptionSettings"]
