#!/usr/bin/env python3
"""根级 ``simulation``：回测执行假设（盯盘 / 买卖价模型 / 滑点 / 边角），与 ``fees`` 等同模式。

- **trigger**：信号由扫描步骤决定，不在此块配置。
- **template**（``standard`` / ``strict`` / ``ideal`` / ``extreme``）：预设快照；settings 仅写 ``template``（及 ``retention``）。
- **template**（``custom``）：必须提供 monitor/buy/sell 价模型，并可配置 slippage、edges、skip_investment_when 等。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Literal, Optional, Tuple, TypeVar

from core.modules.strategy.engines.shared.helpers.participation import (
    ParticipationOnExceed,
    parse_max_participation_rate,
    parse_participation_on_exceed,
)

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
SimulationExecutionMode = Literal["entity_timeline", "calendar_slice"]

DEFAULT_SIMULATION_EXECUTION_MODE: SimulationExecutionMode = "entity_timeline"
DEFAULT_SLICE_OPEN_DAYS = 63
MIN_SLICE_OPEN_DAYS = 5
MAX_SLICE_OPEN_DAYS = 252

PRESET_SIMULATION_TEMPLATE_NAMES = frozenset({"standard", "strict", "ideal", "extreme"})
KNOWN_SIMULATION_TEMPLATES = PRESET_SIMULATION_TEMPLATE_NAMES | frozenset({"custom"})

# 已移除的 edges 键（validate 报 critical）
_REMOVED_SIMULATION_EDGE_KEYS: Dict[str, str] = {
    "skip_limit_up_buy": "改用 simulation.edges.allow_buy_at_limit_up",
    "skip_limit_down_sell": "改用 simulation.edges.allow_sell_at_limit_down",
}

_SIMULATION_DETAIL_KEYS = frozenset(
    {
        "monitor_price_model",
        "buy_price_model",
        "sell_price_model",
        "slippage",
        "edges",
        "extreme_same_bar_order",
        "extreme_same_bar_random_seed",
        "skip_investment_when",
        "liquidity",
        "max_participation_rate",
        "participation_on_exceed",
    }
)

# calendar_slice 调度参数不属于 simulation；误写时报 critical
_SIMULATION_FORBIDDEN_KEYS: Dict[str, str] = {
    "slice_open_days": "calendar_slice 片宽由运行时 auto 决定，不可在 simulation 配置",
    "slice_steps": "calendar_slice 片步数由运行时 auto 决定，不可在 simulation 配置",
    "slice_length": "calendar_slice 片长度由运行时 auto 决定，不可在 simulation 配置",
    "min_required_records": "应配置在 data.min_required_records",
}


@dataclass(frozen=True)
class _ParsedSnapshot:
    template: str
    monitor_price_model: MonitorPriceModel
    buy_price_model: TradePriceModel
    sell_price_model: TradePriceModel
    slippage_buy_bps: float
    slippage_sell_bps: float
    edges_no_next_bar: NoNextBarPolicy
    allow_buy_at_limit_up: bool
    allow_sell_at_limit_down: bool
    extreme_same_bar_order: ExtremeSameBarOrder
    extreme_same_bar_random_seed: Optional[int]
    skip_investment_when: Tuple[str, ...]
    max_participation_rate: float
    participation_on_exceed: ParticipationOnExceed


def canonical_simulation_template_id(raw: Any) -> str:
    """将 settings 规范为合法 ``simulation.template``。"""
    t = str(raw or "").strip().lower()
    if t == "":
        return "standard"
    if t in KNOWN_SIMULATION_TEMPLATES:
        return t
    raise ValueError(
        f"simulation.template 非法: {raw!r}；"
        f"允许: {', '.join(sorted(KNOWN_SIMULATION_TEMPLATES))}"
    )


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


def _realistic_daily_snapshot(
    *,
    template: str,
    allow_at_limit: bool,
    skip_investment_when: Tuple[str, ...],
    max_participation_rate: float = 0.1,
    participation_on_exceed: ParticipationOnExceed = "clip",
) -> _ParsedSnapshot:
    return _ParsedSnapshot(
        template=template,
        monitor_price_model=MonitorPriceModel.CLOSE,
        buy_price_model=TradePriceModel.NEXT_OPEN,
        sell_price_model=TradePriceModel.CLOSE,
        slippage_buy_bps=0.0,
        slippage_sell_bps=0.0,
        edges_no_next_bar="use_last_close",
        allow_buy_at_limit_up=allow_at_limit,
        allow_sell_at_limit_down=allow_at_limit,
        extreme_same_bar_order=ExtremeSameBarOrder.STOP_FIRST,
        extreme_same_bar_random_seed=None,
        skip_investment_when=skip_investment_when,
        max_participation_rate=max_participation_rate,
        participation_on_exceed=participation_on_exceed,
    )


def _default_snapshot_for_template(tmpl: str) -> _ParsedSnapshot:
    t = canonical_simulation_template_id(tmpl)
    if t == "standard":
        return _realistic_daily_snapshot(
            template="standard",
            allow_at_limit=False,
            skip_investment_when=(),
            max_participation_rate=0.1,
            participation_on_exceed="clip",
        )
    if t == "strict":
        return _realistic_daily_snapshot(
            template="strict",
            allow_at_limit=False,
            skip_investment_when=("st", "star_st"),
            max_participation_rate=0.1,
            participation_on_exceed="skip",
        )
    if t == "ideal":
        return _realistic_daily_snapshot(
            template="ideal",
            allow_at_limit=True,
            skip_investment_when=(),
            max_participation_rate=0.1,
            participation_on_exceed="clip",
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
            allow_buy_at_limit_up=True,
            allow_sell_at_limit_down=True,
            extreme_same_bar_order=ExtremeSameBarOrder.STOP_FIRST,
            extreme_same_bar_random_seed=None,
            skip_investment_when=(),
            max_participation_rate=0.1,
            participation_on_exceed="skip",
        )
    if t == "custom":
        return _default_snapshot_for_template("standard")
    raise ValueError(f"simulation.template 非法: {tmpl!r}")


def simulation_template_defaults_payload(tmpl: str) -> Dict[str, Any]:
    """工作台只读展示：某 preset / custom 基线的嵌套 dict（与表单字段一致）。"""
    snap = _default_snapshot_for_template(tmpl)
    seed = snap.extreme_same_bar_random_seed
    return {
        "monitor_price_model": snap.monitor_price_model.value,
        "buy_price_model": snap.buy_price_model.value,
        "sell_price_model": snap.sell_price_model.value,
        "slippage": {
            "buy_bps": snap.slippage_buy_bps,
            "sell_bps": snap.slippage_sell_bps,
        },
        "edges": {
            "no_next_bar": snap.edges_no_next_bar,
            "allow_buy_at_limit_up": snap.allow_buy_at_limit_up,
            "allow_sell_at_limit_down": snap.allow_sell_at_limit_down,
        },
        "extreme_same_bar_order": snap.extreme_same_bar_order.value,
        "extreme_same_bar_random_seed": seed if seed is not None else "",
        "skip_investment_when": list(snap.skip_investment_when),
        "liquidity": {
            "max_participation_rate": snap.max_participation_rate,
            "participation_on_exceed": snap.participation_on_exceed,
        },
    }


def _parse_liquidity_from_raw(
    raw: Dict[str, Any],
    *,
    default_rate: float,
    default_on_exceed: ParticipationOnExceed,
) -> Tuple[float, ParticipationOnExceed]:
    liq = raw.get("liquidity")
    block: Dict[str, Any] = liq if isinstance(liq, dict) else {}
    rate_raw = block.get("max_participation_rate", raw.get("max_participation_rate"))
    exceed_raw = block.get("participation_on_exceed", raw.get("participation_on_exceed"))
    rate = parse_max_participation_rate(
        rate_raw if rate_raw is not None and rate_raw != "" else default_rate,
        default=default_rate,
    )
    on_exceed = (
        parse_participation_on_exceed(exceed_raw)
        if exceed_raw is not None and exceed_raw != ""
        else default_on_exceed
    )
    return rate, on_exceed


def _is_preset_template(tmpl: str) -> bool:
    try:
        t = canonical_simulation_template_id(tmpl)
    except ValueError:
        return False
    return t in PRESET_SIMULATION_TEMPLATE_NAMES


def _parse_custom_snapshot(raw: Dict[str, Any]) -> _ParsedSnapshot:
    from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
        parse_skip_investment_when,
    )

    base = _default_snapshot_for_template("custom")
    monitor = raw.get("monitor_price_model")
    buy = raw.get("buy_price_model")
    sell = raw.get("sell_price_model")
    if monitor is None or buy is None or sell is None:
        raise ValueError(
            "simulation.template 为 custom 时必须提供 "
            "monitor_price_model、buy_price_model、sell_price_model"
        )
    monitor_m = _enum_value(MonitorPriceModel, monitor, "simulation.monitor_price_model")
    buy_m = _enum_value(TradePriceModel, buy, "simulation.buy_price_model")
    sell_m = _enum_value(TradePriceModel, sell, "simulation.sell_price_model")

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
    allow_buy_at_limit_up = base.allow_buy_at_limit_up
    allow_sell_at_limit_down = base.allow_sell_at_limit_down
    if edges is not None:
        if not isinstance(edges, dict):
            raise ValueError("simulation.edges 必须为 dict")
        nnb_raw = edges.get("no_next_bar", nnb)
        nnb_s = str(nnb_raw).strip().lower() if nnb_raw is not None else "use_last_close"
        allowed: Tuple[NoNextBarPolicy, ...] = ("use_last_close", "skip_trade", "unfinished")
        if nnb_s not in allowed:
            raise ValueError(f"simulation.edges.no_next_bar 非法: {nnb_raw!r}；允许 {list(allowed)}")
        nnb = nnb_s  # type: ignore[assignment]
        if "allow_buy_at_limit_up" in edges:
            allow_buy_at_limit_up = bool(edges.get("allow_buy_at_limit_up"))
        if "allow_sell_at_limit_down" in edges:
            allow_sell_at_limit_down = bool(edges.get("allow_sell_at_limit_down"))

    skip = parse_skip_investment_when(raw.get("skip_investment_when", ()))
    max_rate, on_exceed = _parse_liquidity_from_raw(
        raw,
        default_rate=base.max_participation_rate,
        default_on_exceed=base.participation_on_exceed,
    )

    return _ParsedSnapshot(
        template="custom",
        monitor_price_model=monitor_m,
        buy_price_model=buy_m,
        sell_price_model=sell_m,
        slippage_buy_bps=buy_bps,
        slippage_sell_bps=sell_bps,
        edges_no_next_bar=nnb,
        allow_buy_at_limit_up=allow_buy_at_limit_up,
        allow_sell_at_limit_down=allow_sell_at_limit_down,
        extreme_same_bar_order=order,
        extreme_same_bar_random_seed=seed_out,
        skip_investment_when=skip,
        max_participation_rate=max_rate,
        participation_on_exceed=on_exceed,
    )


def _parse_snapshot(raw: Dict[str, Any]) -> _ParsedSnapshot:
    tmpl = canonical_simulation_template_id(raw.get("template"))
    if tmpl == "custom":
        return _parse_custom_snapshot(raw)
    return _default_snapshot_for_template(tmpl)


def _apply_simulation_template_default(sim: Dict[str, Any]) -> None:
    """省略 template 时写入 ``standard``。"""
    raw_tpl = sim.get("template")
    if raw_tpl is None or str(raw_tpl).strip() == "":
        sim["template"] = "standard"


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
        sim.setdefault("template", "standard")
        _apply_simulation_template_default(sim)
        tmpl = str(sim.get("template") or "standard").strip().lower()
        if tmpl != "custom":
            return
        sim.setdefault("slippage", {})
        if not isinstance(sim["slippage"], dict):
            sim["slippage"] = {}
        sim["slippage"].setdefault("buy_bps", 0.0)
        sim["slippage"].setdefault("sell_bps", 0.0)
        sim.setdefault("edges", {})
        if not isinstance(sim["edges"], dict):
            sim["edges"] = {}
        sim["edges"].setdefault("no_next_bar", "use_last_close")
        edges = sim["edges"]
        edges.setdefault("allow_buy_at_limit_up", False)
        edges.setdefault("allow_sell_at_limit_down", False)
        if "skip_investment_when" not in sim:
            sim["skip_investment_when"] = []
        elif sim.get("skip_investment_when") is None:
            sim["skip_investment_when"] = []
        sim.setdefault("liquidity", {})
        if not isinstance(sim["liquidity"], dict):
            sim["liquidity"] = {}
        liq = sim["liquidity"]
        liq.setdefault("max_participation_rate", 0.1)
        liq.setdefault("participation_on_exceed", "clip")

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
    def allow_buy_at_limit_up(self) -> bool:
        return self._parsed.allow_buy_at_limit_up

    @property
    def allow_sell_at_limit_down(self) -> bool:
        return self._parsed.allow_sell_at_limit_down

    @property
    def extreme_same_bar_order(self) -> ExtremeSameBarOrder:
        return self._parsed.extreme_same_bar_order

    @property
    def extreme_same_bar_random_seed(self) -> Optional[int]:
        return self._parsed.extreme_same_bar_random_seed

    @property
    def skip_investment_when(self) -> Tuple[str, ...]:
        return self._parsed.skip_investment_when

    @property
    def max_participation_rate(self) -> float:
        return self._parsed.max_participation_rate

    @property
    def participation_on_exceed(self) -> ParticipationOnExceed:
        return self._parsed.participation_on_exceed

    @property
    def execution_mode(self) -> SimulationExecutionMode:
        raw = self.simulation.get("execution_mode")
        if raw is None or str(raw).strip() == "":
            return DEFAULT_SIMULATION_EXECUTION_MODE
        mode = str(raw).strip().lower()
        if mode in ("entity_timeline", "calendar_slice"):
            return mode  # type: ignore[return-value]
        raise ValueError(
            f"simulation.execution_mode 非法: {raw!r}；允许 entity_timeline | calendar_slice"
        )

    @property
    def slice_open_days(self) -> int:
        raise AttributeError(
            "simulation.slice_open_days 不可配置；calendar_slice 片宽由运行时 planner 决定"
        )

    def _validate_execution_mode(self, result: ValidationReport) -> None:
        try:
            _ = self.execution_mode
        except ValueError as exc:
            SettingsBase.add_critical(result, "simulation.execution_mode", str(exc))

    def _validate_forbidden_simulation_keys(self, result: ValidationReport) -> None:
        for key, message in _SIMULATION_FORBIDDEN_KEYS.items():
            if key not in self.simulation:
                continue
            SettingsBase.add_critical(result, f"simulation.{key}", message)

    def _validate_liquidity(self, result: ValidationReport) -> None:
        try:
            tmpl = canonical_simulation_template_id(self.simulation.get("template", "standard"))
        except ValueError:
            return
        if tmpl != "custom":
            return
        try:
            _parse_liquidity_from_raw(
                self.simulation,
                default_rate=0.1,
                default_on_exceed="clip",
            )
        except ValueError as exc:
            SettingsBase.add_critical(result, "simulation.liquidity", str(exc))

    def _validate_skip_investment_when(self, result: ValidationReport) -> None:
        try:
            tmpl = canonical_simulation_template_id(self.simulation.get("template", "standard"))
        except ValueError:
            return
        if tmpl != "custom":
            return
        try:
            from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
                parse_skip_investment_when,
            )

            _ = parse_skip_investment_when(self.simulation.get("skip_investment_when"))
        except ValueError as exc:
            SettingsBase.add_critical(result, "simulation.skip_investment_when", str(exc))

    def _validate_preset_template_no_detail_overrides(self, result: ValidationReport) -> None:
        sim = self.simulation
        raw_tpl = sim.get("template")
        try:
            tmpl = canonical_simulation_template_id(raw_tpl if raw_tpl is not None else "standard")
        except ValueError as exc:
            SettingsBase.add_critical(result, "simulation.template", str(exc))
            return
        if not _is_preset_template(tmpl):
            return
        for key in _SIMULATION_DETAIL_KEYS:
            if key in sim:
                SettingsBase.add_critical(
                    result,
                    f"simulation.{key}",
                    f"template={tmpl!r} 为预设，不允许设置 {key!r}；"
                    "请仅写 template，或改用 template: \"custom\" 后逐项配置",
                )

    def _validate_removed_edge_keys(self, result: ValidationReport) -> None:
        edges = self.simulation.get("edges")
        if not isinstance(edges, dict):
            return
        for key, hint in _REMOVED_SIMULATION_EDGE_KEYS.items():
            if key in edges:
                SettingsBase.add_critical(
                    result,
                    f"simulation.edges.{key}",
                    f"已移除 {key!r}；{hint}",
                )
        nnb = edges.get("no_next_bar")
        if nnb is not None and str(nnb).strip().lower() == "mark_unfinished":
            SettingsBase.add_critical(
                result,
                "simulation.edges.no_next_bar",
                "已移除 mark_unfinished；改用 unfinished",
            )

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        sim = self.raw_settings.get("simulation")
        if sim is not None and not isinstance(sim, dict):
            SettingsBase.add_critical(result, "simulation", "simulation 必须为 dict")
            return result
        if isinstance(sim, dict):
            self._validate_preset_template_no_detail_overrides(result)
            self._validate_forbidden_simulation_keys(result)
        self.apply_defaults()
        self._validate_removed_edge_keys(result)
        self._validate_execution_mode(result)
        self._validate_liquidity(result)
        self._validate_skip_investment_when(result)
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
    "DEFAULT_SIMULATION_EXECUTION_MODE",
    "DEFAULT_SLICE_OPEN_DAYS",
    "ExtremeSameBarOrder",
    "KNOWN_SIMULATION_TEMPLATES",
    "MAX_SLICE_OPEN_DAYS",
    "MIN_SLICE_OPEN_DAYS",
    "MonitorPriceModel",
    "NoNextBarPolicy",
    "PRESET_SIMULATION_TEMPLATE_NAMES",
    "SimulationExecutionMode",
    "StrategySimulationSettings",
    "TradePriceModel",
    "canonical_simulation_template_id",
    "simulation_template_defaults_payload",
]
