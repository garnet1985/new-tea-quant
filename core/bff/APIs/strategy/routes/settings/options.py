"""Strategy settings option catalogs for UI (V2-04).

Aligned with strategy settings model
(``portfolio`` / ``sampling`` / ``assumption`` / ``risk_control``).
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.market_profile.core.markets import get_available_markets
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    _VALID_MODES,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.sampling_settings import (
    _KNOWN_STRATEGIES,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.assumption_templates import (
    AssumptionTemplate,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.risk_control import (
    StatusTagPolicy,
)

from .const import (
    MARKET_RULES_LABELS,
    PORTFOLIO_ALLOCATION_META,
    RISK_CONTROL_META,
    SAMPLING_META,
    SIMULATION_TEMPLATE_META,
)


class StrategySettingsOptions:
    """V2-04 option lists for settings form controls."""

    @classmethod
    def items_portfolio(cls) -> List[Dict[str, Any]]:
        """``portfolio.allocation.mode`` 可选值。"""
        ordered = ("equal_capital", "equal_shares", "kelly", "custom")
        modes = [m for m in ordered if m in _VALID_MODES]
        rest = sorted(m for m in _VALID_MODES if m not in modes)
        return cls._labeled_items(modes + rest, PORTFOLIO_ALLOCATION_META)

    @classmethod
    def items_sampling(cls) -> List[Dict[str, Any]]:
        """根级 ``sampling.strategy`` 可选值。"""
        ordered = (
            "continuous",
            "uniform",
            "stratified",
            "random",
            "weighted",
            "pool",
            "blacklist",
        )
        keys = [k for k in ordered if k in _KNOWN_STRATEGIES]
        rest = sorted(k for k in _KNOWN_STRATEGIES if k not in keys)
        return cls._labeled_items(keys + rest, SAMPLING_META)

    @classmethod
    def items_risk_control(cls) -> List[Dict[str, Any]]:
        """``simulation.risk_control.skip_enter_when`` 可选标签。"""
        known = StatusTagPolicy.KNOWN_TAGS
        ordered = ("st", "star_st")
        keys = [k for k in ordered if k in known]
        rest = sorted(k for k in known if k not in keys)
        return cls._labeled_items(keys + rest, RISK_CONTROL_META)

    @classmethod
    def items_simulation(cls) -> List[Dict[str, Any]]:
        """``simulation.assumption.template`` 可选值；``defaults`` 为嵌套 tradability。"""
        ordered = ("standard", "strict", "ideal", "extreme", "none", "custom")
        keys = [k for k in ordered if k in AssumptionTemplate.KNOWN]
        rest = sorted(k for k in AssumptionTemplate.KNOWN if k not in keys)
        out: List[Dict[str, Any]] = []
        for key in keys + rest:
            meta = SIMULATION_TEMPLATE_META.get(key)
            if meta:
                label, tooltip = meta
                row: Dict[str, Any] = {
                    "value": key,
                    "label": label,
                    "tooltip": tooltip,
                }
            else:
                row = {"value": key, "label": key}
            row["defaults"] = cls._template_defaults_payload(key)
            out.append(row)
        return out

    @classmethod
    def items_market_rules(cls) -> List[Dict[str, Any]]:
        """根级 ``market_profile`` 可选值。"""
        out: List[Dict[str, Any]] = []
        for pid in get_available_markets():
            out.append(
                {
                    "value": pid,
                    "label": MARKET_RULES_LABELS.get(pid, pid),
                }
            )
        return out

    @classmethod
    def _template_defaults_payload(cls, template: str) -> Dict[str, Any]:
        """Nested defaults for FED merge under ``simulation.assumption``."""
        try:
            key = AssumptionTemplate.canonicalize(template)
        except ValueError:
            return {}
        if key not in AssumptionTemplate.NAMED:
            return {}
        return {"tradability": AssumptionTemplate.tradability_dict(key)}

    @staticmethod
    def _labeled_items(
        keys: List[str],
        meta_map: Dict[str, tuple],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for key in keys:
            meta = meta_map.get(key)
            if meta:
                label, tooltip = meta
                out.append({"value": key, "label": label, "tooltip": tooltip})
            else:
                out.append({"value": key, "label": key})
        return out


__all__ = ["StrategySettingsOptions"]
