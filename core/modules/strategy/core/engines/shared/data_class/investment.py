"""Investment — simulated lifecycle for an ``Opportunity`` signal.

Three kinds of runtime data
---------------------------
1. **Run deps** (``Investment.deps``, set at ``create_from_opportunity``): ``market_rules``,
   ``open_dates``, ``goal``, price models — fixed for the investment run.
2. **Accumulators** (``InvestmentTickState`` on ``Investment``): ``entry``, ``holding``,
   ``extreme``, ``completed_goals``, … — updated each ``tick``.
3. **Tick input** (``InvestmentTickInput``, passed per step, not stored): ``as_of_date``,
   ``data_as_of``, ``bar`` — supplied by the backtester / enumerator loop.

``tick`` orchestrates entry → accumulator updates → goal evaluation → exit.
Returns ``True`` while the tracker should keep this investment in the active bucket;
``False`` when it is ``COMPLETE`` (ready to leave the active bucket).

Lifecycle (MVP — see TODOs on ``Investment``)
----------------------------------------------
- ``PENDING_TO_ENTER``: default; waiting for ``buy_price_model`` fill (e.g. next open).
- ``OPEN``: entered; normal tracking.
- ``PENDING_TO_EXIT``: ``pending_exit`` armed; fill deferred (next_open) or retry (future).
- ``COMPLETE``: done (including ``settle`` force-close).

TODO(investment lifecycle — not yet implemented)
------------------------------------------------
- Tradability via ``market_profile`` (limit up/down, suspended) → block fill, stay pending.
- ``exit_ratio < 1`` partial exit → ``OPEN`` not ``COMPLETE``.
- Full ``buy_price_model`` / ``sell_price_model`` matrix beyond next_open | open | close.
- Distinguish scheduled ``next_open`` defer vs failed-fill retry in ``PENDING_TO_EXIT``.
- Non-trading / missing bar days (simulator currently skips).
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    OpportunityContributor,
    OpportunityMeta,
    StockInfo,
)

if TYPE_CHECKING:
    from core.modules.market_profile.core.base.market_base_rules import MarketBaseRules
    from core.modules.strategy.core.engines.shared.services.strategy_settings.goal_settings import (
        GoalSettings,
    )
    from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
        StrategySettings,
    )


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Lifecycle(str, Enum):
    """Investment state machine."""

    OPEN = "open"
    PENDING_TO_ENTER = "pending_to_enter"  # default; awaiting entry fill
    PENDING_TO_EXIT = "pending_to_exit"  # exit armed; awaiting fill / retry
    COMPLETE = "complete"  # archived; includes simulate-end force close


class ExitReason(str, Enum):
    EXPIRED = "expired"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    SIMULATE_END = "simulate_end"


class InvestmentResult(str, Enum):
    WIN = "win"
    LOSS = "loss"


class ExpirationMode(str, Enum):
    NATURAL_DAY = "natural_day"
    TRADING_DAY = "trading_day"
    OPEN_DAY = "open_day"


class ExecuteStep(str, Enum):
    """``simulation.execute_steps`` entries; each maps to an ``Investment`` handler."""

    CHECK_SETTLEMENT = "check_settlement"
    CHECK_STOP_LOSS = "check_stop_loss"
    CHECK_TAKE_PROFIT = "check_take_profit"
    CHECK_EXPIRATION = "check_expiration"

    @classmethod
    def parse(cls, value: Any) -> "ExecuteStep":
        text = str(value or "").strip().lower()
        if not text:
            raise ValueError("execute step must be a non-empty string")
        try:
            return cls(text)
        except ValueError as exc:
            allowed = ", ".join(step.value for step in cls)
            raise ValueError(f"unknown execute step {value!r}; allowed: {allowed}") from exc


DEFAULT_EXECUTE_STEPS: Tuple[ExecuteStep, ...] = (
    ExecuteStep.CHECK_SETTLEMENT,
    ExecuteStep.CHECK_STOP_LOSS,
    ExecuteStep.CHECK_TAKE_PROFIT,
    ExecuteStep.CHECK_EXPIRATION,
)

EXIT_TRIGGER_EXECUTE_STEPS: Tuple[ExecuteStep, ...] = (
    ExecuteStep.CHECK_STOP_LOSS,
    ExecuteStep.CHECK_TAKE_PROFIT,
    ExecuteStep.CHECK_EXPIRATION,
)


@dataclass(frozen=True)
class ExpirationRule:
    window_days: int
    mode: ExpirationMode


@dataclass(frozen=True)
class InvestmentTickInput:
    """Per-tick external input from the enumerator / backtester (not stored on ``Investment``).

    Only ``as_of_date`` + ``bar`` are required. ``next_open`` fills happen on a *later*
    tick's ``bar`` (``PENDING_TO_EXIT``), never by peeking at a future bar in the same call.
    """

    as_of_date: str
    bar: Dict[str, Any]
    data_as_of: str = ""

    @property
    def pit_as_of(self) -> str:
        return str(self.data_as_of or self.as_of_date or "").strip()


class BarPrices:
    """从 K 线 bar dict 读取价格（顶层 qfq；``raw`` 为不复权）。"""

    @classmethod
    def field(cls, bar: Dict[str, Any], name: str, *, use_raw: bool = False) -> float:
        source = cls._source(bar, use_raw=use_raw)
        if not source:
            return 0.0
        try:
            return float(source.get(name) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def for_model(cls, bar: Dict[str, Any], model: str, *, use_raw: bool = False) -> float:
        """按 ``simulation.*_price_model`` 从当前 bar 取价。

        ``next_open`` 表示在本 tick 用 ``open`` 成交（延后到下一根 open 由调用方门控）。
        """
        key = str(model or "close").strip().lower()
        if key == "next_open":
            return cls.field(bar, "open", use_raw=use_raw)
        if key in {"open", "high", "low", "close", "pre_close"}:
            return cls.field(bar, key, use_raw=use_raw)
        source = cls._source(bar, use_raw=use_raw)
        if key in source:
            return cls.field(bar, key, use_raw=use_raw)
        raise ValueError(f"unsupported price model: {model!r}")

    @classmethod
    def _source(cls, bar: Dict[str, Any], *, use_raw: bool) -> Dict[str, Any]:
        if not isinstance(bar, dict):
            return {}
        if not use_raw:
            return bar
        raw = bar.get("raw")
        return raw if isinstance(raw, dict) else {}


@dataclass(frozen=True)
class InvestmentRunDeps:
    """Run-scoped deps — injected once at ``create_from_opportunity`` (``Investment.deps``)."""

    market_rules: Any
    open_dates: Tuple[str, ...]
    goal: "GoalSettings"
    execute_steps: Tuple[ExecuteStep, ...]
    buy_price_model: str = "next_open"
    sell_price_model: str = "close"
    monitor_price_model: str = "close"

    @classmethod
    def from_settings(
        cls,
        *,
        settings: "StrategySettings",
        market_rules: Any,
        open_dates: Sequence[str],
    ) -> "InvestmentRunDeps":
        from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings import (
            resolve_execute_steps,
        )

        raw = settings.raw_settings
        simulation = raw.get("simulation") if isinstance(raw.get("simulation"), dict) else {}
        return cls(
            market_rules=market_rules,
            open_dates=tuple(open_dates),
            goal=settings.goal,
            execute_steps=tuple(resolve_execute_steps(raw)),
            buy_price_model=str(simulation.get("buy_price_model") or "next_open"),
            sell_price_model=str(simulation.get("sell_price_model") or "close"),
            monitor_price_model=str(simulation.get("monitor_price_model") or "close"),
        )


@dataclass
class EntryInfo:
    entry_price: float = 0.0
    entry_price_raw: float = 0.0
    entry_date: str = ""
    direction: TradeSide = TradeSide.BUY


@dataclass
class ExitInfo:
    exit_price: Optional[float] = None
    exit_price_raw: Optional[float] = None
    exit_date: str = ""
    exit_reason: str = ""
    exit_ratio: float = 0.0


@dataclass
class PendingExit:
    reason: str = ""
    exit_ratio: float = 1.0
    goal_name: str = ""


@dataclass
class HoldingState:
    mode: Optional[ExpirationMode] = None
    window_days: int = 0
    days: int = 0
    last_bar_date: str = ""
    trading_day_count: int = 0
    counter_initialized: bool = False


@dataclass
class ExtremePriceEdge:
    highest: Optional[float] = None
    lowest: Optional[float] = None
    highest_date: str = ""
    lowest_date: str = ""
    highest_return: Optional[float] = None
    lowest_return: Optional[float] = None


# TODO: below goals are dynamically injected when simulating, is triggered by goal extra actions
# @dataclass
# class DynamicGoalState:
#     protect_loss_is_on: bool = False
#     dynamic_loss_is_on: bool = False
#     dynamic_loss_peak: Optional[float] = None


@dataclass
class GoalOutcome:
    result: Optional[InvestmentResult] = None
    weighted_roi: float = 0.0
    price_return: Optional[float] = None
    max_drawdown: Optional[float] = None


@dataclass
class InvestmentTickState:
    """Per-investment accumulators updated across ``tick`` calls."""

    state: Lifecycle = Lifecycle.PENDING_TO_ENTER
    entry: EntryInfo = field(default_factory=EntryInfo)
    exit_info: ExitInfo = field(default_factory=ExitInfo)
    pending_exit: Optional[PendingExit] = None
    holding: HoldingState = field(default_factory=HoldingState)
    extreme: ExtremePriceEdge = field(default_factory=ExtremePriceEdge)
    outcome: GoalOutcome = field(default_factory=GoalOutcome)
    completed_goals: List[Dict[str, Any]] = field(default_factory=list)
    customized_state: Dict[str, Any] = field(default_factory=dict)
    # TODO: active_goals — typed ``Goal`` list when goal pipeline is refactored
    # TODO: dynamic goal flags (protect_loss, dynamic_loss) from goal extra actions


@dataclass
class Investment(Opportunity):
    """Extends ``Opportunity`` with simulation state (signal + runtime + deps)."""

    runtime_state: InvestmentTickState = field(default_factory=InvestmentTickState)
    deps: Optional[InvestmentRunDeps] = None
    execute_steps: List[ExecuteStep] = field(default_factory=list)
    # TODO: ``init_state`` snapshot (frozen entry context) separate from ``deps``

    _EXECUTE_STEP_HANDLERS: ClassVar[Dict[ExecuteStep, str]] = {
        ExecuteStep.CHECK_SETTLEMENT: "_check_settlement",
        ExecuteStep.CHECK_STOP_LOSS: "_check_stop_loss",
        ExecuteStep.CHECK_TAKE_PROFIT: "_check_take_profit",
        ExecuteStep.CHECK_EXPIRATION: "_check_expiration",
    }

    @property
    def lifecycle(self) -> Lifecycle:
        return self.runtime_state.state

    @lifecycle.setter
    def lifecycle(self, value: Lifecycle) -> None:
        self.runtime_state.state = value

    @property
    def entry(self) -> EntryInfo:
        return self.runtime_state.entry

    @entry.setter
    def entry(self, value: EntryInfo) -> None:
        self.runtime_state.entry = value

    @property
    def exit_info(self) -> ExitInfo:
        return self.runtime_state.exit_info

    @exit_info.setter
    def exit_info(self, value: ExitInfo) -> None:
        self.runtime_state.exit_info = value

    @property
    def pending_exit(self) -> Optional[PendingExit]:
        return self.runtime_state.pending_exit

    @pending_exit.setter
    def pending_exit(self, value: Optional[PendingExit]) -> None:
        self.runtime_state.pending_exit = value

    @property
    def holding(self) -> HoldingState:
        return self.runtime_state.holding

    @holding.setter
    def holding(self, value: HoldingState) -> None:
        self.runtime_state.holding = value

    @property
    def extreme(self) -> ExtremePriceEdge:
        return self.runtime_state.extreme

    @extreme.setter
    def extreme(self, value: ExtremePriceEdge) -> None:
        self.runtime_state.extreme = value

    @property
    def outcome(self) -> GoalOutcome:
        return self.runtime_state.outcome

    @outcome.setter
    def outcome(self, value: GoalOutcome) -> None:
        self.runtime_state.outcome = value

    @property
    def completed_goals(self) -> List[Dict[str, Any]]:
        return self.runtime_state.completed_goals

    @property
    def run_deps(self) -> InvestmentRunDeps:
        if self.deps is None:
            raise RuntimeError("Investment 未绑定 deps（须通过 create_from_opportunity 创建）")
        return self.deps

    @classmethod
    def create_from_opportunity(
        cls,
        opportunity: Opportunity,
        *,
        settings: "StrategySettings",
        open_dates: Sequence[str],
    ) -> "Investment":
        from core.infra.project_context import ProjectContext
        from core.modules.market_profile.core.markets import create_market_rules

        profile = str(
            opportunity.market_profile or ProjectContext.config.get_default_market_profile_key()
        ).strip()
        run_deps = InvestmentRunDeps.from_settings(
            settings=settings,
            market_rules=create_market_rules(profile),
            open_dates=open_dates,
        )
        expiration = cls._expiration_rule_from_goal(run_deps.goal.expiration)
        return cls(
            stock=opportunity.stock,
            record_of_today=dict(opportunity.record_of_today),
            trigger_date=str(opportunity.trigger_date or ""),
            trigger_price=float(opportunity.trigger_price or 0.0),
            trigger_price_raw=float(opportunity.trigger_price_raw or 0.0),
            market_profile=profile,
            meta=cls._copy_dataclass(opportunity.meta, OpportunityMeta),
            contributor=cls._copy_dataclass(opportunity.contributor, OpportunityContributor),
            extra_fields=dict(opportunity.extra_fields),
            metadata=dict(opportunity.metadata),
            deps=run_deps,
            runtime_state=InvestmentTickState(
                state=Lifecycle.PENDING_TO_ENTER,
                holding=cls._holding_from_expiration(expiration),
            ),
            execute_steps=list(run_deps.execute_steps),
        )

    def to_dict(self) -> Dict[str, Any]:
        """JSON/CSV-safe export (omits non-serializable run deps such as market_rules)."""
        payload = Opportunity.to_dict(self)
        state = asdict(self.runtime_state)
        state["state"] = self.lifecycle.value
        payload.update(
            {
                "lifecycle": self.lifecycle.value,
                "runtime_state": state,
                "entry": asdict(self.entry),
                "exit_info": asdict(self.exit_info),
                "holding": asdict(self.holding),
                "extreme": asdict(self.extreme),
                "outcome": asdict(self.outcome),
                "completed_goals": list(self.completed_goals),
                "execute_steps": [step.value for step in self._resolve_execute_steps()],
            }
        )
        if self.pending_exit is not None:
            payload["pending_exit"] = asdict(self.pending_exit)
        return payload

    def _resolve_execute_steps(self) -> List[ExecuteStep]:
        if self.execute_steps:
            return list(self.execute_steps)
        return list(self.run_deps.execute_steps)

    def tick(self, tick_input: InvestmentTickInput) -> bool:
        """Review and update this investment for one calendar step.

        Returns ``True`` if the tracker should keep ticking this investment;
        ``False`` when ``lifecycle`` is ``COMPLETE`` (ready to leave the active bucket).
        """
        as_of = str(tick_input.as_of_date or "").strip()
        bar = tick_input.bar

        if self.lifecycle == Lifecycle.COMPLETE:
            return False

        if self.lifecycle == Lifecycle.PENDING_TO_ENTER:
            if self._is_able_to_enter(as_of, bar):
                self._apply_enter(as_of, bar)
                self.lifecycle = Lifecycle.OPEN
                self._update_extremes(as_of, bar)
            return True

        if self.lifecycle == Lifecycle.PENDING_TO_EXIT:
            if self._is_able_to_exit(as_of, bar):
                self._apply_exit(as_of, bar)
                # TODO: partial exit (exit_ratio < 1) → Lifecycle.OPEN
                self.lifecycle = Lifecycle.COMPLETE
                return False
            return True

        if self.lifecycle == Lifecycle.OPEN:
            self._update_extremes(as_of, bar)
            self._update_holding(as_of)
            if self._evaluate_goals(as_of, bar):
                if self._should_defer_exit(as_of, bar):
                    self.lifecycle = Lifecycle.PENDING_TO_EXIT
                    return True
                if self._is_able_to_exit(as_of, bar):
                    self._apply_exit(as_of, bar)
                    # TODO: partial exit (exit_ratio < 1) → Lifecycle.OPEN
                    self.lifecycle = Lifecycle.COMPLETE
                    return False
                # TODO: tradability blocked fill — retry on later ticks
                self.lifecycle = Lifecycle.PENDING_TO_EXIT
            return True

        return True

    def _evaluate_goals(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """Run ``simulation.execute_steps`` in order; True if an exit trigger fired."""
        for step in self._resolve_execute_steps():
            if step == ExecuteStep.CHECK_SETTLEMENT:
                if not self._check_settlement(as_of):
                    return False
                continue
            handler_name = self._EXECUTE_STEP_HANDLERS[step]
            if getattr(self, handler_name)(as_of, bar):
                return True
        return False

    def _check_settlement(self, as_of: str) -> bool:
        """Gate: False blocks remaining steps for this bar."""
        if self.lifecycle != Lifecycle.OPEN:
            return True
        entry_date = str(self.entry.entry_date or "").strip()
        if not entry_date:
            return True
        held = self._settlement_days_held(entry_date, as_of, self.run_deps.open_dates)
        return self.run_deps.market_rules.is_allowed_to_sell(held)

    def _check_stop_loss(self, as_of: str, bar: Dict[str, Any]) -> bool:
        stage = self.run_deps.goal.stop_loss
        if self.lifecycle != Lifecycle.OPEN or stage is None:
            return False
        basis = float(self.entry.entry_price or self.trigger_price or 0.0)
        if basis <= 0:
            return False
        stop_price = self.run_deps.goal.exit_price(stage, basis)
        if float(bar["low"]) <= stop_price:
            self.pending_exit = PendingExit(
                reason=ExitReason.STOP_LOSS.value,
                exit_ratio=stage.exit_ratio,
                goal_name=stage.name,
            )
            return True
        return False

    def _check_take_profit(self, as_of: str, bar: Dict[str, Any]) -> bool:
        stage = self.run_deps.goal.take_profit
        if self.lifecycle != Lifecycle.OPEN or stage is None:
            return False
        basis = float(self.entry.entry_price or self.trigger_price or 0.0)
        if basis <= 0:
            return False
        target_price = self.run_deps.goal.exit_price(stage, basis)
        if float(bar["high"]) >= target_price:
            self.pending_exit = PendingExit(
                reason=ExitReason.TAKE_PROFIT.value,
                exit_ratio=stage.exit_ratio,
                goal_name=stage.name,
            )
            return True
        return False

    def _check_expiration(self, as_of: str, bar: Dict[str, Any]) -> bool:
        _ = bar
        if self.lifecycle != Lifecycle.OPEN:
            return False
        if self.holding.window_days <= 0 or self.holding.mode is None:
            return False
        entry_date = str(self.entry.entry_date or "").strip()
        if not entry_date:
            return False
        held = self._holding_days(entry_date, as_of, self.holding.mode, self.run_deps.open_dates)
        self.holding.days = held
        if held >= self.holding.window_days:
            self.pending_exit = PendingExit(
                reason=ExitReason.EXPIRED.value,
                exit_ratio=1.0,
                goal_name="expiration",
            )
            return True
        return False

    def _should_defer_exit(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """True when ``sell_price_model`` requires a later tick to fill (MVP: ``next_open`` only).

        TODO: extend for other models / tradability-driven deferrals.
        """
        _ = (as_of, bar)
        model = str(self.run_deps.sell_price_model or "close").strip().lower()
        return model == "next_open"

    def _is_able_to_enter(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """Whether this tick can fill entry per ``buy_price_model`` (no mutation)."""
        return self._resolve_entry_price(as_of, bar) is not None

    def _apply_enter(self, as_of: str, bar: Dict[str, Any]) -> None:
        price = self._resolve_entry_price(as_of, bar)
        if price is None:
            return
        raw_price = self._resolve_entry_price(as_of, bar, use_raw=True)
        self.entry = EntryInfo(
            entry_price=price,
            entry_price_raw=float(raw_price or 0.0),
            entry_date=str(as_of or "").strip(),
            direction=TradeSide.BUY,
        )

    def _resolve_entry_price(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        use_raw: bool = False,
    ) -> Optional[float]:
        """Entry fill price for this tick, or ``None`` if not ready.

        Controlled by ``run_deps.buy_price_model`` (``next_open`` | ``open`` | ``close``).
        ``use_raw=True`` 时从 ``bar["raw"]`` 取同一 model 对应字段。
        TODO: tradability gate before returning a price.
        """
        if self.lifecycle != Lifecycle.PENDING_TO_ENTER:
            return None

        trigger = str(self.trigger_date or "").strip()
        as_of = str(as_of or "").strip()
        if not trigger or not as_of:
            return None

        model = str(self.run_deps.buy_price_model or "next_open").strip().lower()
        open_dates = self.run_deps.open_dates
        if model == "next_open":
            if as_of <= trigger or not self._is_first_open_after(trigger, as_of, open_dates):
                return None
        elif model in {"close", "open"}:
            if as_of != trigger:
                return None
        else:
            raise ValueError(f"unsupported buy_price_model: {model!r}")

        price = BarPrices.for_model(bar, model, use_raw=use_raw)
        if price <= 0:
            return None
        return price

    def _is_able_to_exit(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        price_model: Optional[str] = None,
    ) -> bool:
        """Whether this tick can fill exit per ``sell_price_model`` (no mutation).

        TODO: ``market_profile`` tradability (limit up/down, suspended, T+N already in goals).
        """
        return self._resolve_exit_price(as_of, bar, price_model=price_model) is not None

    def _apply_exit(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        price_model: Optional[str] = None,
    ) -> bool:
        """Record exit leg from ``pending_exit``. Returns ``True`` if fill applied."""
        exit_price = self._resolve_exit_price(as_of, bar, price_model=price_model)
        if exit_price is None or self.pending_exit is None:
            return False

        ratio = float(self.pending_exit.exit_ratio or 1.0)
        basis = float(self.entry.entry_price or self.trigger_price or 0.0)
        profit = exit_price - basis
        roi = (profit / basis) if basis > 0 else 0.0
        exit_price_raw = self._resolve_exit_price(
            as_of, bar, price_model=price_model, use_raw=True
        )

        self.completed_goals.append(
            {
                "name": self.pending_exit.goal_name or self.pending_exit.reason,
                "date": as_of,
                "price": exit_price,
                "price_raw": float(exit_price_raw or 0.0),
                "exit_ratio": ratio,
                "profit": profit,
                "weighted_profit": profit * ratio,
                "reason": self.pending_exit.reason,
                "roi": roi,
            }
        )

        self.exit_info = ExitInfo(
            exit_price=exit_price,
            exit_price_raw=float(exit_price_raw or 0.0),
            exit_date=as_of,
            exit_reason=self.pending_exit.reason,
            exit_ratio=ratio,
        )
        self.outcome.price_return = roi
        self.outcome.weighted_roi = roi * ratio
        self.outcome.result = InvestmentResult.WIN if roi >= 0 else InvestmentResult.LOSS
        # custom goal 无 expiration 时 holding.days 可能一直未更新；退出时补齐
        entry_date = str(self.entry.entry_date or "").strip()
        if entry_date and int(self.holding.days or 0) <= 0:
            mode = self.holding.mode or ExpirationMode.OPEN_DAY
            self.holding.days = self._holding_days(
                entry_date, as_of, mode, self.run_deps.open_dates
            )
            self.holding.last_bar_date = as_of
        self.pending_exit = None
        return True

    def _resolve_exit_price(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        price_model: Optional[str] = None,
        use_raw: bool = False,
    ) -> Optional[float]:
        """Exit fill price for this tick, or ``None`` if not ready / not allowed."""
        _ = as_of
        if self.pending_exit is None:
            return None
        if self.lifecycle not in (Lifecycle.OPEN, Lifecycle.PENDING_TO_EXIT):
            return None

        model = str(price_model or self.run_deps.sell_price_model or "close").strip().lower()
        exit_price = BarPrices.for_model(bar, model, use_raw=use_raw)
        if exit_price <= 0:
            return None
        # TODO: tradability — return None when limit up/down blocks sell at exit_price
        return exit_price

    def settle(self, tick_input: InvestmentTickInput) -> bool:
        """Force-close at simulate end. Returns ``False`` (stop tracking)."""
        if self.lifecycle == Lifecycle.COMPLETE:
            return False
        if self.lifecycle == Lifecycle.PENDING_TO_ENTER:
            self.lifecycle = Lifecycle.COMPLETE
            return False
        self.pending_exit = PendingExit(
            reason=ExitReason.SIMULATE_END.value,
            exit_ratio=1.0,
            goal_name="simulate_end",
        )
        as_of = str(tick_input.as_of_date or "").strip()
        if self.lifecycle in (Lifecycle.OPEN, Lifecycle.PENDING_TO_EXIT):
            self._apply_exit(as_of, tick_input.bar, price_model="close")
        self.lifecycle = Lifecycle.COMPLETE
        return False

    def _update_extremes(self, as_of: str, bar: Dict[str, Any]) -> None:
        if self.lifecycle != Lifecycle.OPEN:
            return
        basis = float(self.entry.entry_price or 0.0)
        if basis <= 0:
            return
        high = float(bar.get("high") or bar.get("close") or 0.0)
        low = float(bar.get("low") or bar.get("close") or 0.0)
        if high <= 0 or low <= 0:
            return
        if self.extreme.highest is None or high > self.extreme.highest:
            self.extreme.highest = high
            self.extreme.highest_date = as_of
            self.extreme.highest_return = (high - basis) / basis
        if self.extreme.lowest is None or low < self.extreme.lowest:
            self.extreme.lowest = low
            self.extreme.lowest_date = as_of
            self.extreme.lowest_return = (low - basis) / basis

    def _update_holding(self, as_of: str) -> None:
        if self.lifecycle != Lifecycle.OPEN or self.holding.mode is None:
            return
        entry_date = str(self.entry.entry_date or "").strip()
        if not entry_date:
            return
        self.holding.days = self._holding_days(
            entry_date, as_of, self.holding.mode, self.run_deps.open_dates
        )
        self.holding.last_bar_date = as_of
        self.holding.counter_initialized = True

    @staticmethod
    def _copy_dataclass(value: Any, cls: type) -> Any:
        if isinstance(value, cls):
            return cls(**{f.name: getattr(value, f.name) for f in fields(cls)})
        if isinstance(value, dict):
            return cls(**{f.name: value.get(f.name, "") for f in fields(cls)})
        return cls()

    @staticmethod
    def _expiration_rule_from_goal(expiration: Optional[Any]) -> Optional[ExpirationRule]:
        if expiration is None:
            return None
        return ExpirationRule(
            window_days=expiration.window_days,
            mode=ExpirationMode(expiration.mode),
        )

    @staticmethod
    def _holding_from_expiration(expiration: Optional[ExpirationRule]) -> HoldingState:
        if expiration is None:
            return HoldingState()
        return HoldingState(mode=expiration.mode, window_days=expiration.window_days)

    @staticmethod
    def _open_days_inclusive(start_date: str, end_date: str, open_dates: Sequence[str]) -> int:
        start = str(start_date).strip()
        end = str(end_date).strip()
        if not start or not end or not open_dates:
            return 0
        if start > end:
            return 0
        start_idx = bisect_left(open_dates, start)
        end_idx = bisect_left(open_dates, end)
        if start_idx >= len(open_dates) or open_dates[start_idx] != start:
            return 0
        if end_idx >= len(open_dates) or open_dates[end_idx] != end:
            return 0
        return end_idx - start_idx + 1

    @classmethod
    def _settlement_days_held(cls, entry_date: str, as_of: str, open_dates: Sequence[str]) -> int:
        """Trading days held for settlement (entry day does not count toward T+N)."""
        inclusive = cls._open_days_inclusive(entry_date, as_of, open_dates)
        return max(inclusive - 1, 0)

    @classmethod
    def _holding_days(
        cls,
        entry_date: str,
        as_of: str,
        mode: ExpirationMode,
        open_dates: Sequence[str],
    ) -> int:
        if mode in (ExpirationMode.OPEN_DAY, ExpirationMode.TRADING_DAY):
            return cls._open_days_inclusive(entry_date, as_of, open_dates)
        try:
            start_dt = datetime.strptime(str(entry_date).strip(), "%Y%m%d")
            end_dt = datetime.strptime(str(as_of).strip(), "%Y%m%d")
            return max((end_dt - start_dt).days, 0)
        except ValueError:
            return 0

    @staticmethod
    def _is_first_open_after(trigger: str, as_of: str, open_dates: Sequence[str]) -> bool:
        idx = bisect_left(open_dates, trigger)
        if idx < len(open_dates) and open_dates[idx] == trigger:
            next_idx = idx + 1
        else:
            next_idx = idx
        return next_idx < len(open_dates) and open_dates[next_idx] == as_of


__all__ = [
    "DEFAULT_EXECUTE_STEPS",
    "EXIT_TRIGGER_EXECUTE_STEPS",
    "BarPrices",
    "EntryInfo",
    "ExecuteStep",
    "ExitInfo",
    "ExitReason",
    "ExpirationMode",
    "ExpirationRule",
    "ExtremePriceEdge",
    "HoldingState",
    "Investment",
    "InvestmentRunDeps",
    "InvestmentTickInput",
    "InvestmentTickState",
    "InvestmentResult",
    "GoalOutcome",
    "Lifecycle",
    "PendingExit",
    "TradeSide",
]
