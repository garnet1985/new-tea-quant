"""``settings.portfolio`` — 资金模拟与 allocation 配置。

本文件:
- AllocationConfig / OutputConfig / PortfolioSettings
  边界: 负责 portfolio section；不负责 EnterSelection 或 PortfolioSimulator 回放
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .settings_base import SettingsBase
from .validation_report import ValidationReport

_VALID_MODES = frozenset({"equal_capital", "equal_shares", "kelly", "custom"})
_ORDER_WORDS = frozenset({"ASC", "DESC"})


@dataclass(frozen=True)
class OpportunitySelectionRule:
    """一条选仓规则。``direction`` 与 ``weight`` 互斥，由列表整体决定。"""

    field: str
    src: str = ""
    direction: str = ""
    weight: float = 0.0

    def snapshot_key(self, base_data_key: str = "") -> str:
        """主数据字段不带前缀；其他数据源为 ``data_key.field``。"""
        src = str(self.src or "").strip()
        base = str(base_data_key or "").strip()
        if not src or (base and src == base):
            return self.field
        return f"{src}.{self.field}"


@dataclass
class AllocationConfig:
    """``settings.portfolio.allocation``。"""

    mode: str = "equal_capital"
    max_portfolio_size: int = 10
    max_weight_per_stock: float = 0.3
    lots_per_trade: int = 1
    kelly_fraction: float = 0.5
    skip_trade_when_insufficient: bool = False
    opportunity_selection: Tuple[OpportunitySelectionRule, ...] = ()

    @property
    def opportunity_selection_mode(self) -> str:
        """``""`` 不排序；``order`` 多关键字；``weight`` 加权。"""
        if not self.opportunity_selection:
            return ""
        if self.opportunity_selection[0].direction:
            return "order"
        return "weight"


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
        self._validate_opportunity_selection(report)
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
            opportunity_selection=self._selection_rules(a.get("opportunity_selection")),
        )

    def _parse_output(self) -> OutputConfig:
        o = self.portfolio.get("output") or {}
        if not isinstance(o, dict):
            o = {}
        return OutputConfig(
            save_trades=bool(o.get("save_trades", True)),
            save_equity_curve=bool(o.get("save_equity_curve", True)),
        )

    def _validate_opportunity_selection(self, report: ValidationReport) -> None:
        block = self.portfolio.get("allocation")
        if not isinstance(block, dict) or "opportunity_selection" not in block:
            return
        canonical, error = _canonicalize_opportunity_selection(
            block.get("opportunity_selection")
        )
        if error:
            SettingsBase.add_critical(
                report,
                "portfolio.allocation.opportunity_selection",
                error,
                suggested_fix=(
                    '[{"close": "DESC"}, {"pe": "ASC"}] 或 '
                    '[{"close": 20}, {"pe": -80}]'
                ),
            )
            return
        block["opportunity_selection"] = list(canonical or [])

    @staticmethod
    def _selection_rules(raw: Any) -> Tuple[OpportunitySelectionRule, ...]:
        canonical, error = _canonicalize_opportunity_selection(raw)
        if error or not canonical:
            return ()
        rules: List[OpportunitySelectionRule] = []
        for item in canonical:
            field = next(key for key in item if key != "src")
            src = str(item.get("src") or "")
            value = item[field]
            if isinstance(value, str):
                rules.append(
                    OpportunitySelectionRule(
                        field=field, src=src, direction=value
                    )
                )
            else:
                rules.append(
                    OpportunitySelectionRule(
                        field=field, src=src, weight=float(value)
                    )
                )
        return tuple(rules)

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


def _canonicalize_opportunity_selection(
    raw: Any,
) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """缺省返回 ``(None, "")``。合法时返回规范列表；非法时第二项为错误说明。"""
    if raw is None:
        return None, ""
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        return None, "opportunity_selection 须为 list"
    items = list(raw)
    if not items:
        return [], ""

    canonical: List[Dict[str, Any]] = []
    kinds: List[str] = []
    seen: List[Tuple[str, str]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not item:
            return None, f"opportunity_selection[{index}] 须为非空 dict"
        src_raw = item.get("src") if "src" in item else ""
        if "src" in item:
            if not isinstance(src_raw, str) or not src_raw.strip():
                return None, f"opportunity_selection[{index}].src 须为非空字符串"
            src = src_raw.strip()
        else:
            src = ""
        fields = [str(key).strip() for key in item.keys() if str(key) != "src"]
        if len(fields) != 1 or not fields[0]:
            return None, (
                f"opportunity_selection[{index}] 恰好写一个字段，"
                "src 只能作为可选项"
            )
        field = fields[0]
        if field == "src":
            return None, f"opportunity_selection[{index}] 字段名不能是 src"
        pair = (field, src)
        if pair in seen:
            return None, f"opportunity_selection 重复字段 {field}" + (
                f"（src={src}）" if src else ""
            )
        seen.append(pair)
        value = next(item[key] for key in item if str(key).strip() == field)
        kind, normalized, error = _normalize_selection_value(value)
        if error:
            return None, f"opportunity_selection[{index}].{field} {error}"
        kinds.append(kind)
        row: Dict[str, Any] = {field: normalized}
        if src:
            row["src"] = src
        canonical.append(row)

    if len(set(kinds)) > 1:
        return None, "opportunity_selection 不能同时写 ASC/DESC 和权重"
    if kinds and kinds[0] == "weight" and all(
        float(row[next(key for key in row if key != "src")]) == 0.0
        for row in canonical
    ):
        return [], ""
    return canonical, ""


def _normalize_selection_value(value: Any) -> Tuple[str, Any, str]:
    if isinstance(value, str):
        word = value.strip().upper()
        if word in _ORDER_WORDS:
            return "order", word, ""
        return "", None, "须为 ASC、DESC 或数字权重"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "", None, "须为 ASC、DESC 或数字权重"
    return "weight", value, ""


__all__ = [
    "AllocationConfig",
    "OpportunitySelectionRule",
    "OutputConfig",
    "PortfolioSettings",
]
