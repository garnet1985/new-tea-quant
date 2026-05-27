#!/usr/bin/env python3
"""goal.stock_status_risk_management — 股票状态持仓风控（退市恒生效 + 可选 ST/*ST 规则）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from .settings_base import SettingsBase, ValidationReport

KNOWN_RULE_NAMES = frozenset({"st", "star_st"})
KNOWN_DELISTED_EXIT_PRICES = frozenset({"last_tradable_close", "same_bar_close"})


@dataclass(frozen=True)
class StockStatusRiskRule:
    name: str
    close_invest: bool = True
    sell_ratio: float = 1.0


@dataclass(frozen=True)
class StockStatusRiskManagementSettings:
    """
    - ``rules`` 为空：仅引擎内置退市强平（不可关闭）。
    - ``rules`` 可含 ``st`` / ``star_st``；不得含 ``delisted``。
    """

    rules: Tuple[StockStatusRiskRule, ...] = ()
    delisted_exit_price: str = "last_tradable_close"

    @classmethod
    def from_goal_block(cls, raw: Any) -> "StockStatusRiskManagementSettings":
        if raw is None:
            return cls()
        if isinstance(raw, list):
            return cls._from_rules_list(raw)
        if isinstance(raw, dict):
            rules_raw = raw.get("rules", [])
            if rules_raw is None:
                rules_raw = []
            if not isinstance(rules_raw, list):
                raise ValueError("goal.stock_status_risk_management.rules 必须为 list")
            exit_px = str(
                raw.get("delisted_exit_price") or "last_tradable_close"
            ).strip()
            base = cls._from_rules_list(rules_raw)
            return cls(
                rules=base.rules,
                delisted_exit_price=exit_px or "last_tradable_close",
            )
        raise ValueError(
            "goal.stock_status_risk_management 须为 list（仅 rules）或 "
            "dict（rules + 可选 delisted_exit_price）"
        )

    @classmethod
    def _from_rules_list(cls, rules_raw: List[Any]) -> "StockStatusRiskManagementSettings":
        rules: List[StockStatusRiskRule] = []
        for idx, item in enumerate(rules_raw):
            if not isinstance(item, dict):
                raise ValueError(
                    f"goal.stock_status_risk_management.rules[{idx}] 必须为 dict"
                )
            name = str(item.get("name") or "").strip().lower()
            if name == "delisted":
                raise ValueError(
                    "goal.stock_status_risk_management 不支持 name=delisted；"
                    "退市强平由引擎默认启用"
                )
            if name not in KNOWN_RULE_NAMES:
                raise ValueError(
                    f"goal.stock_status_risk_management.rules[{idx}].name "
                    f"非法: {name!r}；允许: {sorted(KNOWN_RULE_NAMES)}"
                )
            close_invest = bool(item.get("close_invest", False))
            sell_ratio = float(item.get("sell_ratio", 0.0) or 0.0)
            if close_invest:
                sell_ratio = 1.0
            elif sell_ratio <= 0:
                sell_ratio = 1.0
                close_invest = True
            rules.append(
                StockStatusRiskRule(
                    name=name,
                    close_invest=close_invest,
                    sell_ratio=sell_ratio,
                )
            )
        return cls(rules=tuple(rules))

    def apply_defaults_to_goal_block(self, goal: Dict[str, Any]) -> None:
        raw = goal.get("stock_status_risk_management")
        if raw is None:
            return
        if isinstance(raw, list):
            goal["stock_status_risk_management"] = {"rules": list(raw)}
            return
        if isinstance(raw, dict):
            if "rules" not in raw:
                raw["rules"] = []
            if not raw.get("delisted_exit_price"):
                raw["delisted_exit_price"] = "last_tradable_close"

    @staticmethod
    def validate_block(
        goal_config: Dict[str, Any],
        field_path: str = "goal.stock_status_risk_management",
    ) -> ValidationReport:
        result = SettingsBase.new_validation()
        raw = goal_config.get("stock_status_risk_management")
        if raw is None:
            return result
        try:
            parsed = StockStatusRiskManagementSettings.from_goal_block(raw)
        except ValueError as exc:
            SettingsBase.add_critical(result, field_path, str(exc))
            return result
        if parsed.delisted_exit_price not in KNOWN_DELISTED_EXIT_PRICES:
            SettingsBase.add_critical(
                result,
                f"{field_path}.delisted_exit_price",
                f"非法: {parsed.delisted_exit_price!r}；"
                f"允许: {sorted(KNOWN_DELISTED_EXIT_PRICES)}",
            )
        names = [r.name for r in parsed.rules]
        if len(names) != len(set(names)):
            SettingsBase.add_critical(
                result,
                field_path,
                "rules 中 name 不可重复",
            )
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules": [
                {
                    "name": r.name,
                    "close_invest": r.close_invest,
                    **({} if r.close_invest else {"sell_ratio": r.sell_ratio}),
                }
                for r in self.rules
            ],
            "delisted_exit_price": self.delisted_exit_price,
        }


__all__ = [
    "KNOWN_DELISTED_EXIT_PRICES",
    "KNOWN_RULE_NAMES",
    "StockStatusRiskManagementSettings",
    "StockStatusRiskRule",
]
