"""``simulation.assumption`` — template + 有效 tradability + target_check_order。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

from .assumption_templates import AssumptionTemplate
from .tradability import TradabilityConfig

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.investment import (
        TargetCheckStep,
    )

_DEFAULT_TARGET_CHECK_ORDER = [
    "check_stop_loss",
    "check_take_profit",
    "check_expiration",
]


@dataclass
class AssumptionSettings(SettingsBase):
    """``settings.simulation.assumption``。

    命名 ``template`` 短路 → 预设 tradability；``none`` / ``custom`` → 显式块。
    ``target_check_order``：``check_targets`` 内 SL/TP/expire 短路顺序（同 bar 冲突裁决）。
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

    @property
    def target_check_order(self) -> List[str]:
        raw = self.assumption.get("target_check_order")
        if not isinstance(raw, list) or not raw:
            return list(_DEFAULT_TARGET_CHECK_ORDER)
        return [str(item).strip() for item in raw if str(item).strip()]

    def parsed_target_check_order(self) -> List["TargetCheckStep"]:
        from core.modules.strategy.core.engines.shared.data_class.investment import (
            TargetCheckStep,
        )

        self.apply_defaults()
        return [TargetCheckStep.parse(item) for item in self.target_check_order]

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

        if (
            "target_check_order" not in assumption
            or not isinstance(assumption.get("target_check_order"), list)
            or not assumption.get("target_check_order")
        ):
            assumption["target_check_order"] = list(_DEFAULT_TARGET_CHECK_ORDER)

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
        self._validate_target_check_order(report)

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

    def _validate_target_check_order(self, report: ValidationReport) -> None:
        from core.modules.strategy.core.engines.shared.data_class.investment import (
            TargetCheckStep,
        )

        raw = self.assumption.get("target_check_order")
        if not isinstance(raw, list) or not raw:
            SettingsBase.add_critical(
                report,
                "simulation.assumption.target_check_order",
                "target_check_order must be a non-empty list",
                suggested_fix=f"Use default: {_DEFAULT_TARGET_CHECK_ORDER}",
            )
            return

        seen: set[str] = set()
        for idx, item in enumerate(raw):
            field_path = f"simulation.assumption.target_check_order[{idx}]"
            try:
                step = TargetCheckStep.parse(item)
            except ValueError as exc:
                SettingsBase.add_critical(
                    report,
                    field_path,
                    str(exc),
                    suggested_fix=f"Allowed: {[s.value for s in TargetCheckStep]}",
                )
                continue
            if step.value in seen:
                SettingsBase.add_critical(
                    report,
                    field_path,
                    f"duplicate target check step: {step.value!r}",
                )
                continue
            seen.add(step.value)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "template": self.template or AssumptionTemplate.NONE,
            "tradability": self.tradability.to_dict(),
            "target_check_order": list(self.target_check_order),
        }


__all__ = ["AssumptionSettings"]
