#!/usr/bin/env python3
"""根级 ``simulation``：回测执行假设（盯盘 / 买卖价模型 / 滑点 / 边角），与 ``fees`` 等同模式。

- **trigger**：信号由扫描步骤决定，不在此块配置。
- **盯盘 / 买 / 卖**：通过属性读取已解析的枚举与数值；引擎从 ``StrategySimulationSettings`` 实例上直接取。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Literal, Optional, Tuple, TypeVar

from .settings_base import SettingsBase, ValidationReport

_E = TypeVar("_E")


class MonitorPriceModel(str, Enum):
    """持仓盯盘：每日用哪种价判断止盈/止损/到期等。"""

    CLOSE = "close"
    EXTREME = "extreme"


class TradePriceModel(str, Enum):
    """真实成交记账：从 K 线按哪种语义取理论价（具体 bar 由引擎实现）。"""

    CLOSE = "close"
    OPEN = "open"
    NEXT_OPEN = "next_open"
    EXTREME = "extreme"


class ExtremeSameBarOrder(str, Enum):
    """极值盯盘时，同一根日线内先止损还是先止盈 / 随机。"""

    STOP_FIRST = "stop_first"
    TAKE_PROFIT_FIRST = "take_profit_first"
    RANDOM = "random"


NoNextBarPolicy = Literal["use_last_close", "skip_trade", "unfinished"]

# 工作台表单 ``simulation.template`` 合法取值（与 ``_default_snapshot_for_template`` 一致）
KNOWN_SIMULATION_TEMPLATES = frozenset({"deterministic", "extreme", "custom"})


@dataclass(frozen=True)
class _ParsedSnapshot:
    template: str
    monitor_price_model: MonitorPriceModel
    buy_price_model: TradePriceModel
    sell_price_model: TradePriceModel
    slippage_buy_bps: float
    slippage_sell_bps: float
    edges_no_next_bar: NoNextBarPolicy
    extreme_same_bar_order: ExtremeSameBarOrder
    extreme_same_bar_random_seed: Optional[int]


def _enum_value(enum_cls: type[_E], raw: Any, field: str) -> _E:
    if isinstance(raw, enum_cls):
        return raw
    if raw is None or raw == "":
        raise ValueError(f"{field} 不能为空")
    key = str(raw).strip().lower()
    for member in enum_cls:
        if member.value == key:
            return member
    raise ValueError(f"{field} 非法取值: {raw!r}；允许: {[m.value for m in enum_cls]}")


def _optional_enum(enum_cls: type[_E], raw: Any, field: str, default: _E) -> _E:
    if raw is None or raw == "":
        return default
    return _enum_value(enum_cls, raw, field)


def _default_snapshot_for_template(tmpl: str) -> _ParsedSnapshot:
    t = tmpl.strip().lower()
    if t in ("", "deterministic", "default"):
        return _ParsedSnapshot(
            template="deterministic",
            monitor_price_model=MonitorPriceModel.CLOSE,
            buy_price_model=TradePriceModel.NEXT_OPEN,
            sell_price_model=TradePriceModel.CLOSE,
            slippage_buy_bps=0.0,
            slippage_sell_bps=0.0,
            edges_no_next_bar="use_last_close",
            extreme_same_bar_order=ExtremeSameBarOrder.STOP_FIRST,
            extreme_same_bar_random_seed=None,
        )
    if t == "extreme":
        return _ParsedSnapshot(
            template="extreme",
            monitor_price_model=MonitorPriceModel.EXTREME,
            buy_price_model=TradePriceModel.EXTREME,
            sell_price_model=TradePriceModel.EXTREME,
            slippage_buy_bps=0.0,
            slippage_sell_bps=0.0,
            edges_no_next_bar="use_last_close",
            extreme_same_bar_order=ExtremeSameBarOrder.STOP_FIRST,
            extreme_same_bar_random_seed=None,
        )
    if t == "custom":
        return _default_snapshot_for_template("deterministic")
    raise ValueError(f"simulation.template 非法: {tmpl!r}；允许 deterministic | extreme | custom")


def _parse_snapshot(raw: Dict[str, Any]) -> _ParsedSnapshot:
    tmpl = str(raw.get("template") or "deterministic").strip().lower()
    base = _default_snapshot_for_template(tmpl)
    monitor = raw.get("monitor_price_model")
    buy = raw.get("buy_price_model")
    sell = raw.get("sell_price_model")

    if tmpl == "custom":
        if monitor is None or buy is None or sell is None:
            raise ValueError(
                "simulation.template 为 custom 时必须提供 "
                "monitor_price_model、buy_price_model、sell_price_model"
            )
        monitor_m = _enum_value(MonitorPriceModel, monitor, "simulation.monitor_price_model")
        buy_m = _enum_value(TradePriceModel, buy, "simulation.buy_price_model")
        sell_m = _enum_value(TradePriceModel, sell, "simulation.sell_price_model")
    else:
        monitor_m = _optional_enum(
            MonitorPriceModel, monitor, "simulation.monitor_price_model", base.monitor_price_model
        )
        buy_m = _optional_enum(TradePriceModel, buy, "simulation.buy_price_model", base.buy_price_model)
        sell_m = _optional_enum(TradePriceModel, sell, "simulation.sell_price_model", base.sell_price_model)

    order = _optional_enum(
        ExtremeSameBarOrder,
        raw.get("extreme_same_bar_order"),
        "simulation.extreme_same_bar_order",
        base.extreme_same_bar_order,
    )
    seed_raw = raw.get("extreme_same_bar_random_seed")
    if seed_raw is None or seed_raw == "":
        seed_out: Optional[int] = base.extreme_same_bar_random_seed
    else:
        try:
            seed_out = int(seed_raw)
        except (TypeError, ValueError) as e:
            raise ValueError("simulation.extreme_same_bar_random_seed 须为整数或省略") from e

    slip = raw.get("slippage")
    buy_bps, sell_bps = base.slippage_buy_bps, base.slippage_sell_bps
    if slip is not None:
        if not isinstance(slip, dict):
            raise ValueError("simulation.slippage 必须为 dict")
        if "buy_bps" in slip:
            try:
                buy_bps = float(slip.get("buy_bps") or 0.0)
            except (TypeError, ValueError) as e:
                raise ValueError("simulation.slippage.buy_bps 须为数字") from e
        if "sell_bps" in slip:
            try:
                sell_bps = float(slip.get("sell_bps") or 0.0)
            except (TypeError, ValueError) as e:
                raise ValueError("simulation.slippage.sell_bps 须为数字") from e

    edges = raw.get("edges")
    nnb: NoNextBarPolicy = base.edges_no_next_bar
    if edges is not None:
        if not isinstance(edges, dict):
            raise ValueError("simulation.edges 必须为 dict")
        nnb_raw = edges.get("no_next_bar", nnb)
        nnb_s = str(nnb_raw).strip().lower() if nnb_raw is not None else "use_last_close"
        if nnb_s == "mark_unfinished":  # 历史配置别名
            nnb_s = "unfinished"
        allowed: Tuple[NoNextBarPolicy, ...] = ("use_last_close", "skip_trade", "unfinished")
        if nnb_s not in allowed:
            raise ValueError(f"simulation.edges.no_next_bar 非法: {nnb_raw!r}；允许 {list(allowed)}")
        nnb = nnb_s  # type: ignore[assignment]

    resolved_tpl = "extreme" if tmpl == "extreme" else ("custom" if tmpl == "custom" else "deterministic")
    return _ParsedSnapshot(
        template=resolved_tpl,
        monitor_price_model=monitor_m,
        buy_price_model=buy_m,
        sell_price_model=sell_m,
        slippage_buy_bps=buy_bps,
        slippage_sell_bps=sell_bps,
        edges_no_next_bar=nnb,
        extreme_same_bar_order=order,
        extreme_same_bar_random_seed=seed_out,
    )


@dataclass
class StrategySimulationSettings(SettingsBase):
    """附着在 ``StrategySettings.raw_settings`` 上；解析结果通过属性读取。"""

    raw_settings: Dict[str, Any]
    _parsed_cache: Optional[_ParsedSnapshot] = field(default=None, repr=False, init=False)

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategySimulationSettings":
        if not isinstance(root, dict):
            root = {}
        SettingsBase.ensure_dict_block(root, "simulation")
        return cls(raw_settings=root)

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    def apply_defaults(self) -> None:
        object.__setattr__(self, "_parsed_cache", None)
        sim = self.simulation
        sim.setdefault("template", "deterministic")
        sim.setdefault("slippage", {})
        if not isinstance(sim["slippage"], dict):
            sim["slippage"] = {}
        sim["slippage"].setdefault("buy_bps", 0.0)
        sim["slippage"].setdefault("sell_bps", 0.0)
        sim.setdefault("edges", {})
        if not isinstance(sim["edges"], dict):
            sim["edges"] = {}
        sim["edges"].setdefault("no_next_bar", "use_last_close")

    @property
    def _parsed(self) -> _ParsedSnapshot:
        cached = self._parsed_cache
        if cached is not None:
            return cached
        self.apply_defaults()
        built = _parse_snapshot(dict(self.simulation))
        object.__setattr__(self, "_parsed_cache", built)
        return built

    @property
    def template(self) -> str:
        return self._parsed.template

    @property
    def monitor_price_model(self) -> MonitorPriceModel:
        return self._parsed.monitor_price_model

    @property
    def buy_price_model(self) -> TradePriceModel:
        return self._parsed.buy_price_model

    @property
    def sell_price_model(self) -> TradePriceModel:
        return self._parsed.sell_price_model

    @property
    def slippage_buy_bps(self) -> float:
        return self._parsed.slippage_buy_bps

    @property
    def slippage_sell_bps(self) -> float:
        return self._parsed.slippage_sell_bps

    @property
    def edges_no_next_bar(self) -> NoNextBarPolicy:
        return self._parsed.edges_no_next_bar

    @property
    def extreme_same_bar_order(self) -> ExtremeSameBarOrder:
        return self._parsed.extreme_same_bar_order

    @property
    def extreme_same_bar_random_seed(self) -> Optional[int]:
        return self._parsed.extreme_same_bar_random_seed

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        sim = self.raw_settings.get("simulation")
        if sim is not None and not isinstance(sim, dict):
            SettingsBase.add_critical(result, "simulation", "simulation 必须为 dict")
            return result
        self.apply_defaults()
        try:
            object.__setattr__(self, "_parsed_cache", None)
            _ = _parse_snapshot(dict(self.simulation))
        except ValueError as exc:
            SettingsBase.add_critical(result, "simulation", str(exc))
        return result

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return self.deep_copy_dict(dict(self.simulation))


__all__ = [
    "ExtremeSameBarOrder",
    "MonitorPriceModel",
    "NoNextBarPolicy",
    "StrategySimulationSettings",
    "TradePriceModel",
]
